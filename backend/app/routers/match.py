from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

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
    top_k: int = 5,
    user_context: str = "",
):
    payload = request or MatchRequest()
    payload.project_id = project_id
    payload.project = None
    payload.top_k = top_k
    payload.user_context = user_context
    return match(payload)


@router.get("/llm/status")
def llm_status():
    return llm.get_config().status()
