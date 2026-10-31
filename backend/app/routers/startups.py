from typing import List

from fastapi import APIRouter, HTTPException

from .. import startup_matching, store
from ..models import InvestorMatchRequest, Startup, StartupMatchResponse

router = APIRouter(prefix="/startups", tags=["startups"])


@router.get("", response_model=List[Startup])
def list_startups():
    """All illustrative startup profiles (currently all demo records)."""
    return store.list_startups()


@router.get("/{startup_id}", response_model=Startup)
def get_startup(startup_id: str):
    """One startup profile by id, or 404 when it does not exist."""
    startup = store.get_startup(startup_id)
    if startup is None:
        raise HTTPException(status_code=404, detail="Startup not found")
    return startup


@router.post("/match", response_model=StartupMatchResponse)
def match_startups(request: InvestorMatchRequest):
    """Rank demo startup profiles for an investor profile using fixed rules.

    No introduction, contact, or investment decision is created by this
    endpoint. Only criteria with enough information on both sides are scored;
    everything else is returned in ``missing``.
    """
    startups = store.list_startups()
    return startup_matching.run_matching(startups, request)
