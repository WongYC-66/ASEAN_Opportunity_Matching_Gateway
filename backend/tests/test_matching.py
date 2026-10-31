"""Tests for the sponsor-matching heuristic engine and LLM response parsing.

Run from the backend directory:

    .venv/Scripts/pip install -r requirements-dev.txt
    .venv/Scripts/python -m pytest
"""

import pytest

from app import matching
from app.matching import heuristic_rank, run_matching
from app.models import MatchRequest, Project, Sponsor


def make_project(**overrides):
    metrics = {
        "tech_stack": ["python", "react"],
        "domains": ["fintech"],
        "team_size": 4,
        "experience_level": "intermediate",
        "open_source": True,
        "budget_usd": 100,
        "duration_hours": 24,
        "completion_percent": 50,
        "has_demo": True,
    }
    metrics.update(overrides.pop("metrics", {}))
    base = {
        "id": "prj_test",
        "created_at": "2026-10-31T00:00:00Z",
        "title": "Fraud Chatbot",
        "description": "A bot that helps detect fraud",
        "metrics": metrics,
    }
    base.update(overrides)
    return Project(**base)


def make_sponsor(**overrides):
    base = {
        "id": "s99",
        "name": "Test Bank",
        "focus_domains": ["fintech", "banking"],
        "preferred_tech": ["python", "java"],
        "track_name": "Fintech for Good",
        "min_team_size": 2,
        "max_team_size": 5,
        "requires_open_source": True,
        "budget_cap_usd": 500,
        "deadline_hours": 48,
        "keywords": ["fraud"],
    }
    base.update(overrides)
    return Sponsor(**base)


def test_heuristic_ranks_exact_fit_highest():
    project = make_project()
    perfect = make_sponsor()
    distant = make_sponsor(
        id="s0",
        name="Unrelated Corp",
        focus_domains=["automotive"],
        preferred_tech=["rust", "c++"],
        track_name="Autonomous Driving",
        keywords=["self-driving"],
    )
    ranking = heuristic_rank(project, [distant, perfect], user_context="")
    assert ranking[0].sponsor.id == "s99"
    assert ranking[0].score > ranking[1].score
    assert any("python" in reason for reason in ranking[0].reasons)


def test_heuristic_avoids_substring_false_positives():
    project = make_project(metrics={"tech_stack": ["html"]})
    # "ml" must not match inside "html"; only whole tokens count.
    sponsor = make_sponsor(preferred_tech=["ml"], focus_domains=[])
    result = matching.heuristic_score(project, sponsor, user_context="")
    overlap = [r for r in result.reasons if "preferred technologies" in r]
    if overlap:
        assert "1/1" not in overlap[0]


def test_missing_track_name_does_not_break_reasons():
    project = make_project()
    sponsor = make_sponsor(track_name="", keywords=["fraud"])
    result = matching.heuristic_score(project, sponsor, user_context="")
    assert all("''" not in reason for reason in result.reasons)
    assert any("keywords" in reason for reason in result.reasons)


def test_track_match_requires_the_track_name_token():
    project = make_project()
    sponsor = make_sponsor(track_name="Fintech for Good", keywords=["payments"])
    result = matching.heuristic_score(project, sponsor, user_context="")
    # Only the track phrase itself should produce "Speaks to the ..." wording;
    # a bare keyword hit falls back to the generic aligned-with-keywords reason.
    track_reasons = [r for r in result.reasons if "track" in r]
    assert all("Fintech for Good" in r for r in track_reasons)


def test_constraints_produce_gaps():
    project = make_project(
        metrics={
            "tech_stack": ["python", "java"],  # full tech overlap: no tech gap
            "open_source": False,
            "budget_usd": 900,
            "duration_hours": 72,
        }
    )
    sponsor = make_sponsor()
    result = matching.heuristic_score(project, sponsor, user_context="")
    assert any("open-source" in gap for gap in result.gaps)
    assert any("Budget" in gap for gap in result.gaps)
    assert any("deadline" in gap for gap in result.gaps)


def test_run_matching_falls_back_to_heuristic():
    project = make_project()
    request = MatchRequest(project_id="prj_test", top_k=1)
    response = run_matching(project, [make_sponsor()], request)
    assert response.engine == "heuristic"
    assert len(response.matches) == 1
    assert 0 <= response.matches[0].score <= 100


def test_parse_llm_matches_filters_unknown_ids_and_duplicates():
    raw = {
        "summary": "ok",
        "matches": [
            {"sponsor_id": "s99", "score": 80, "reasons": ["fits"], "gaps": []},
            {"sponsor_id": "s99", "score": 90, "reasons": [], "gaps": []},
            {"sponsor_id": "ghost", "score": 99, "reasons": [], "gaps": []},
        ],
    }
    results, summary = matching._parse_llm_matches(raw, [make_sponsor()], top_k=5)
    assert summary == "ok"
    assert [r.sponsor.id for r in results] == ["s99"]
    assert results[0].score == 80.0


def test_parse_llm_accepts_bare_list_and_coerces_bad_score():
    raw = [{"sponsor_id": "s99", "score": "not-a-number", "reasons": ["x"], "gaps": []}]
    results, _ = matching._parse_llm_matches(raw, [make_sponsor()], top_k=5)
    assert results[0].score == 0.0


def test_parse_llm_rejects_garbage():
    with pytest.raises(ValueError):
        matching._parse_llm_matches({"matches": []}, [make_sponsor()], top_k=5)
