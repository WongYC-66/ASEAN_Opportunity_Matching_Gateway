"""API behaviour tests using FastAPI's TestClient.

The `projects.json` data file is snapshotted and restored around each test so
POST-backed tests never leave data behind.
"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECTS_FILE = Path(__file__).resolve().parent.parent / "app" / "data" / "projects.json"

SAMPLE_PROJECT = {
    "title": "Teh Tarik Trend Bot",
    "description": "Analyses teh tarik price trends",
    "team_name": "Team Kopi",
    "metrics": {
        "tech_stack": ["python"],
        "domains": ["fintech"],
        "team_size": 3,
        "experience_level": "beginner",
        "open_source": False,
        "budget_usd": 1000,
        "duration_hours": 72,
    },
}


@pytest.fixture()
def restore_projects_file():
    snapshot = PROJECTS_FILE.read_bytes()
    yield
    PROJECTS_FILE.write_bytes(snapshot)


def test_root_and_health():
    assert client.get("/api/health").json() == {"status": "ok"}
    body = client.get("/").json()
    assert body["message"].startswith("Hack Teh Tarik")
    assert "/docs" in body["endpoints"] or "docs" in body


def test_sponsors_listing_and_lookup():
    sponsors = client.get("/api/sponsors").json()
    assert sponsors
    first_id = sponsors[0]["id"]
    found = client.get(f"/api/sponsors/{first_id}")
    assert found.status_code == 200
    assert found.json()["id"] == first_id
    assert client.get("/api/sponsors/does-not-exist").status_code == 404


def test_project_filters(restore_projects_file):
    created = client.post("/api/projects", json=SAMPLE_PROJECT)
    assert created.status_code == 201
    project = created.json()
    assert project["id"].startswith("prj_")

    listing = client.get("/api/projects").json()
    assert any(row["id"] == project["id"] for row in listing)

    by_tech = client.get("/api/projects", params={"tech": "python"}).json()
    assert all("python" in row["metrics"]["tech_stack"] for row in by_tech)

    by_domain = client.get("/api/projects", params={"domain": "fintech"}).json()
    assert by_domain

    # Unknown experience level simply yields nothing instead of crashing.
    assert client.get("/api/projects", params={"experience": "boss"}).status_code == 200

    single = client.get(f"/api/projects/{project['id']}")
    assert single.json()["title"] == project["title"]
    assert client.get("/api/projects/prj_missing").status_code == 404


def test_match_requires_project_reference():
    assert client.post("/api/match", json={}).status_code == 422


def test_match_inline_project_top_k_is_respected():
    body = {"project": SAMPLE_PROJECT, "top_k": 2}
    response = client.post("/api/match", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "heuristic"
    assert len(data["matches"]) == 2
    scores = [m["score"] for m in data["matches"]]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)


def test_match_project_by_id_body_top_k_not_clobbered_by_query_defaults(
    restore_projects_file,
):
    created = client.post("/api/projects", json=SAMPLE_PROJECT).json()
    # Body asks for 3 results; no query params are sent.
    response = client.post(f"/api/projects/{created['id']}/match", json={"top_k": 3})
    assert response.status_code == 200
    assert len(response.json()["matches"]) == 3


def test_match_unknown_project_is_404():
    response = client.post("/api/projects/prj_missing/match")
    assert response.status_code == 404


def test_match_rejects_out_of_range_top_k():
    response = client.post("/api/projects/prj_x/match", params={"top_k": 99})
    assert response.status_code == 422


def test_llm_status_shape():
    status = client.get("/api/llm/status").json()
    assert set(status) >= {"preset", "available", "mode", "presets"}
    assert status["mode"] in {"llm", "heuristic"}
