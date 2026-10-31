from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from .. import store
from ..models import Project, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[Project])
def list_projects(
    q: Optional[str] = Query(default=None, description="Free-text search"),
    domain: Optional[str] = Query(default=None),
    tech: Optional[str] = Query(default=None),
    experience: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    projects = store.list_projects()
    if q:
        needle = q.lower()
        projects = [
            project
            for project in projects
            if needle in project.title.lower()
            or needle in project.description.lower()
            or needle in project.team_name.lower()
        ]
    if domain:
        needle = domain.lower()
        projects = [
            project
            for project in projects
            if any(needle == item.lower() for item in project.metrics.domains)
        ]
    if tech:
        needle = tech.lower()
        projects = [
            project
            for project in projects
            if any(needle == item.lower() for item in project.metrics.tech_stack)
        ]
    if experience:
        needle = experience.lower()
        projects = [
            project
            for project in projects
            if project.metrics.experience_level.lower() == needle
        ]
    return projects[:limit]


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: str):
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("", response_model=Project, status_code=201)
def submit_project(payload: ProjectCreate):
    return store.add_project(payload)
