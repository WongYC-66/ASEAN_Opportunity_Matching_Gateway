from typing import List

from fastapi import APIRouter, HTTPException

from .. import opportunity_matching, store
from ..models import (
    Opportunity,
    OpportunityMatchRequest,
    OpportunityMatchResponse,
)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=List[Opportunity])
def list_opportunities():
    """All opportunity records (demo and verified) from the backend JSON file."""
    return store.list_opportunities()


@router.post("/match", response_model=OpportunityMatchResponse)
def match_opportunities(request: OpportunityMatchRequest):
    """Rank opportunities for a startup profile using deterministic rules.

    This endpoint does not use an LLM and never decides eligibility. An empty
    profile is valid: every record is returned with score 0 and a neutral
    explanation, which keeps the UI predictable.
    """
    opportunities = store.list_opportunities()
    return opportunity_matching.run_matching(opportunities, request)


@router.get("/{opportunity_id}", response_model=Opportunity)
def get_opportunity(opportunity_id: str):
    opportunity = store.get_opportunity(opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity
