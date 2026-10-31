"""Tests for the opportunity list and rule-based matching endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import Opportunity, OpportunityMatchRequest
from app.opportunity_matching import MAX_SCORE, run_matching, score_opportunity

client = TestClient(app)

SAMPLE_PROFILE = {
    "country": "Malaysia",
    "industry": "Fintech",
    "stage": "Seed",
    "goals": ["Funding"],
    "top_k": 20,
}


def test_opportunities_listing_and_lookup():
    records = client.get("/api/opportunities").json()
    assert len(records) == 12
    assert all(record["dataStatus"] == "demo" for record in records)
    assert all(record["sourceUrl"] is None for record in records)

    first = records[0]
    found = client.get(f"/api/opportunities/{first['id']}")
    assert found.status_code == 200
    assert found.json() == first
    assert client.get("/api/opportunities/does-not-exist").status_code == 404


def test_match_returns_ranked_results_with_reasons():
    response = client.post("/api/opportunities/match", json=SAMPLE_PROFILE)
    assert response.status_code == 200
    data = response.json()

    assert data["engine"] == "rules"
    assert data["model"] == "rules-v1"
    assert data["warning"] is None
    assert len(data["matches"]) == 12

    scores = [match["percent"] for match in data["matches"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= score <= 100 for score in scores)
    assert all(0 <= match["score"] <= MAX_SCORE for match in data["matches"])
    assert all(match["reasons"] for match in data["matches"])

    top = data["matches"][0]
    assert any("Malaysia" in reason for reason in top["reasons"])


def test_exact_country_tie_break_precedes_asean_wide():
    data = client.post("/api/opportunities/match", json=SAMPLE_PROFILE).json()
    names = [match["opportunity"]["name"] for match in data["matches"]]
    assert names.index("AgriFood Innovation Fund - Demo Record") < names.index(
        "ASEAN-Wide Demo Seed Grant (Illustrative)"
    )


def test_match_top_k_is_respected():
    payload = {**SAMPLE_PROFILE, "top_k": 3}
    data = client.post("/api/opportunities/match", json=payload).json()
    assert len(data["matches"]) == 3


def test_match_rejects_out_of_range_top_k():
    payload = {**SAMPLE_PROFILE, "top_k": 0}
    assert client.post("/api/opportunities/match", json=payload).status_code == 422


def test_empty_profile_is_valid_and_neutral():
    data = client.post("/api/opportunities/match", json={}).json()
    assert len(data["matches"]) == 12
    assert all(match["percent"] == 0 for match in data["matches"])
    assert all(match["label"] == "No direct match" for match in data["matches"])


def test_exact_country_scores_higher_than_asean_wide():
    direct = Opportunity.model_validate(
        {
            "id": "direct",
            "name": "Direct",
            "provider": "Provider",
            "category": "Funding",
            "countries": ["Malaysia"],
            "dataStatus": "demo",
        }
    )
    regional = Opportunity.model_validate(
        {
            "id": "regional",
            "name": "Regional",
            "provider": "Provider",
            "category": "Funding",
            "countries": ["ASEAN-wide"],
            "dataStatus": "demo",
        }
    )
    profile = OpportunityMatchRequest(country="Malaysia")

    direct_result = score_opportunity(direct, profile)
    regional_result = score_opportunity(regional, profile)
    assert direct_result[1] > regional_result[1]
    assert any("ASEAN-wide" in reason for reason in regional_result[3])


def test_unknown_target_lists_earn_no_points():
    record = Opportunity.model_validate(
        {
            "id": "unknown",
            "name": "Unknown targets",
            "provider": "Provider",
            "category": "Support",
            "countries": ["Malaysia"],
            "targetStages": None,
            "targetIndustries": None,
            "goals": [],
            "dataStatus": "demo",
        }
    )
    profile = OpportunityMatchRequest(industry="Fintech", stage="Seed")
    _, percent, label, reasons = score_opportunity(record, profile)
    assert percent == 0
    assert label == "No direct match"
    assert "No direct match" in reasons[0]


def test_run_matching_does_not_use_llm(monkeypatch):
    record = Opportunity.model_validate(
        {
            "id": "one",
            "name": "One",
            "provider": "Provider",
            "category": "Funding",
            "countries": ["Malaysia"],
            "dataStatus": "demo",
        }
    )
    response = run_matching([record], OpportunityMatchRequest(country="Malaysia"))
    assert response.engine == "rules"
    assert response.matches[0].percent == 33
