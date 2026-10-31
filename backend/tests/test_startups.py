"""Tests for the investor side of the gateway: startup listing and matching."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import InvestorMatchRequest, Startup
from app.startup_matching import run_matching, score_startup

client = TestClient(app)

INVESTOR_PROFILE = {
    "investorType": "Venture Capital Fund",
    "countries": ["Malaysia", "Singapore"],
    "industries": ["Fintech", "Artificial Intelligence"],
    "stages": ["Pre-seed", "Seed"],
    "ticketMin": 50000,
    "ticketMax": 500000,
    "currency": "USD",
    "strategies": [],
    "goals": ["Discover startups"],
    "description": "",
    "top_k": 20,
}


def _startup(**overrides) -> Startup:
    row = {
        "id": "demo-test",
        "name": "Test Startup (Demo Startup)",
        "description": "A fictional startup used only in tests.",
        "country": "Malaysia",
        "industry": "Fintech",
        "stage": "Seed",
        "businessModel": "Subscription software",
        "revenueStatus": "Revenue-generating",
        "fundingSought": 200000,
        "fundingCurrency": "USD",
        "strategyTags": ["Deep technology"],
        "dataStatus": "demo",
    }
    row.update(overrides)
    return Startup.model_validate(row)


def test_startups_listing_and_lookup():
    records = client.get("/api/startups").json()
    assert len(records) == 8
    assert all(record["dataStatus"] == "demo" for record in records)
    assert all(record["sourceUrl"] is None for record in records)
    assert all(record["lastVerifiedDate"] is None for record in records)
    assert all(record["notes"] for record in records)

    first = records[0]
    found = client.get(f"/api/startups/{first['id']}")
    assert found.status_code == 200
    assert found.json() == first
    assert client.get("/api/startups/does-not-exist").status_code == 404


def test_sample_investor_profile_returns_startups_with_reasons():
    response = client.post("/api/startups/match", json=INVESTOR_PROFILE)
    assert response.status_code == 200
    data = response.json()

    assert data["engine"] == "rules"
    assert data["model"] == "investor-rules-v1"
    assert len(data["matches"]) == 8
    assert data["criteria"]

    scores = [match["percent"] for match in data["matches"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= score <= 100 for score in scores)
    assert all(match["reasons"] for match in data["matches"])

    top = data["matches"][0]
    assert top["startup"]["name"] == "Aksa Health AI (Demo Startup)"
    assert top["percent"] == 100
    assert set(top["assessed"]) == {"Geography", "Industry", "Stage", "Ticket size"}
    assert top["missing"] == [
        "No investment strategies selected, so strategy fit was not assessed."
    ]


def test_currency_mismatch_is_not_compared_and_is_reported_as_missing():
    data = client.post("/api/startups/match", json=INVESTOR_PROFILE).json()
    tanilink = next(
        match
        for match in data["matches"]
        if match["startup"]["id"] == "demo-startup-03"
    )
    # Malaysia + Seed match, Agriculture does not. The MYR requirement is not
    # compared with the investor's USD range.
    assert tanilink["assessed"] == ["Geography", "Industry", "Stage"]
    assert "Ticket size" not in tanilink["assessed"]
    assert any("no currency conversion" in gap for gap in tanilink["missing"])
    assert tanilink["percent"] == 67


def test_incomplete_startup_is_not_penalised_for_unknown_fields():
    payload = {**INVESTOR_PROFILE, "strategies": ["Deep technology"]}
    data = client.post("/api/startups/match", json=payload).json()
    warung = next(
        match
        for match in data["matches"]
        if match["startup"]["id"] == "demo-startup-07"
    )
    assert warung["score"] == 0
    assert "Ticket size" not in warung["assessed"]
    assert any("funding requirement is not recorded" in gap for gap in warung["missing"])
    assert any("Strategy tags are not recorded" in gap for gap in warung["missing"])


def test_missing_information_does_not_lower_a_perfect_match():
    startup = _startup(strategyTags=None, fundingSought=None, fundingCurrency=None)
    profile = InvestorMatchRequest(
        countries=["Malaysia"],
        industries=["Fintech"],
        stages=["Seed"],
        ticketMin=10000,
        ticketMax=100000,
        currency="USD",
    )
    _, percent, label, reasons, missing, assessed = score_startup(startup, profile)
    assert percent == 100
    assert label == "Strong match"
    assert assessed == ["Geography", "Industry", "Stage"]
    assert reasons
    assert len(missing) == 2


def test_data_status_is_never_scored():
    demo = _startup(dataStatus="demo")
    verified = _startup(id="demo-verified", dataStatus="verified")
    profile = InvestorMatchRequest(
        countries=["Malaysia"],
        industries=["Fintech"],
        stages=["Seed"],
    )
    assert score_startup(demo, profile)[:2] == score_startup(verified, profile)[:2]


def test_empty_investor_profile_scores_nothing_but_returns_records():
    data = client.post("/api/startups/match", json={}).json()
    assert len(data["matches"]) == 8
    assert all(match["percent"] == 0 for match in data["matches"])
    assert all(match["assessed"] == [] for match in data["matches"])
    assert data["warning"]


def test_demo_only_warning_is_present():
    data = client.post("/api/startups/match", json=INVESTOR_PROFILE).json()
    assert "fictional demo profile" in data["warning"]


def test_run_matching_top_k_and_tie_order():
    profile = InvestorMatchRequest(countries=["Malaysia"], top_k=2)
    response = run_matching(
        [_startup(id="b", name="B Startup"), _startup(id="a", name="A Startup")],
        profile,
    )
    assert [item.startup.name for item in response.matches] == [
        "A Startup",
        "B Startup",
    ]


def test_match_rejects_invalid_investor_input():
    bad_country = {**INVESTOR_PROFILE, "countries": ["Atlantis"]}
    assert client.post("/api/startups/match", json=bad_country).status_code == 422

    bad_strategy = {**INVESTOR_PROFILE, "strategies": ["Time travel"]}
    assert client.post("/api/startups/match", json=bad_strategy).status_code == 422

    bad_range = {**INVESTOR_PROFILE, "ticketMin": 1000, "ticketMax": 100}
    assert client.post("/api/startups/match", json=bad_range).status_code == 422

    bad_currency = {**INVESTOR_PROFILE, "currency": "EUR"}
    assert client.post("/api/startups/match", json=bad_currency).status_code == 422

    bad_top_k = {**INVESTOR_PROFILE, "top_k": 0}
    assert client.post("/api/startups/match", json=bad_top_k).status_code == 422


def test_startup_listing_is_valid_json_with_required_fields():
    records = client.get("/api/startups").json()
    required = {
        "id",
        "name",
        "description",
        "country",
        "industry",
        "stage",
        "businessModel",
        "revenueStatus",
        "fundingSought",
        "fundingCurrency",
        "strategyTags",
        "dataStatus",
        "sourceUrl",
        "lastVerifiedDate",
        "notes",
    }
    assert all(required <= set(record) for record in records)
    assert len({record["id"] for record in records}) == len(records)
