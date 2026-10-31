import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from .models import Project, ProjectCreate, Sponsor

DATA_DIR = Path(__file__).resolve().parent / "data"
_lock = threading.Lock()


def _read(name: str) -> list:
    path = DATA_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _write(name: str, rows: list) -> None:
    path = DATA_DIR / name
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


_sponsors: List[dict] = _read("sponsors.json")
_projects: List[dict] = _read("projects.json")


def list_sponsors() -> List[Sponsor]:
    return [Sponsor.model_validate(row) for row in _sponsors]


def get_sponsor(sponsor_id: str) -> Optional[Sponsor]:
    for row in _sponsors:
        if row.get("id") == sponsor_id:
            return Sponsor.model_validate(row)
    return None


def list_projects() -> List[Project]:
    return [Project.model_validate(row) for row in _projects]


def get_project(project_id: str) -> Optional[Project]:
    for row in _projects:
        if row.get("id") == project_id:
            return Project.model_validate(row)
    return None


def add_project(payload: ProjectCreate) -> Project:
    project = Project(
        id=f"prj_{uuid4().hex[:8]}",
        created_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    with _lock:
        _projects.append(project.model_dump(mode="json"))
        _write("projects.json", _projects)
    return project
