from typing import List

from fastapi import APIRouter, HTTPException

from .. import store
from ..models import Sponsor

router = APIRouter(prefix="/sponsors", tags=["sponsors"])


@router.get("", response_model=List[Sponsor])
def list_sponsors():
    return store.list_sponsors()


@router.get("/{sponsor_id}", response_model=Sponsor)
def get_sponsor(sponsor_id: str):
    sponsor = store.get_sponsor(sponsor_id)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return sponsor
