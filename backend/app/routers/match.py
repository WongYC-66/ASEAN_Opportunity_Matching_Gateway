from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from .. import llm, matching, store
from ..models import MatchRequest, MatchResponse, Project, ProjectCreate

router = APIRouter(tags=["matching"])


def _resolve_project(request: MatchRequest) -> Project:
    if request.project_id:
        project = store.get_project(request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    if request.project:
        return Project(
            id="draft",
            created_at=datetime.now(timezone.utc),
            **request.project.model_dump(),
        )
    raise HTTPException(
        status_code=422,
        detail="Provide either 'project_id' or an inline 'project' object.",
    )


@router.post("/match", response_model=MatchResponse)
def match(request: MatchRequest):
    project = _resolve_project(request)
    sponsors = store.list_sponsors()
    if not sponsors:
        raise HTTPException(status_code=503, detail="No sponsors configured")
    return matching.run_matching(project, sponsors, request)


@router.post("/projects/{project_id}/match", response_model=MatchResponse)
def match_project(
    project_id: str,
    request: MatchRequest | None = None,
    top_k: int | None = Query(default=None, ge=1, le=20),
    user_context: str | None = Query(default=None, max_length=4000),
):
    # Query params only override the body when explicitly provided, so a JSON
    # body is never silently clobbered by their defaults.
    payload = request or MatchRequest()
    payload.project_id = project_id
    payload.project = None
    if top_k is not None:
        payload.top_k = top_k
    if user_context is not None:
        payload.user_context = user_context
    return match(payload)


@router.get("/llm/status")
def llm_status():
    return llm.get_config().status()
