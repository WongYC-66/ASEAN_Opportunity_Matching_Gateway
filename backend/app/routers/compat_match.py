from typing import List

from fastapi import APIRouter, HTTPException

from .. import matching, store
from ..models import MatchRequest

router = APIRouter(tags=["compatibility-matching"])


@router.post("/opportunities/match")
def match_opportunities(payload: dict):
    # Frontend sends startup profile; we need to convert to our match format
    goals = payload.get("goals") or []
    industry = payload.get("industry") or ""
    stage = payload.get("stage") or ""
    country = payload.get("country") or ""
    description = payload.get("description") or ""
    funding = payload.get("fundingAmount")
    
    # Create a project-like object
    from datetime import datetime, timezone
    from ..models import Project, Metrics, ProjectCreate
    
    metrics = Metrics(
        tech_stack=[],
        domains=[industry.lower()] if industry and industry != "Other" else goals,
        team_size=2,
        experience_level="intermediate",
        team_skills=goals,
        duration_hours=48,
        open_source=True,
        budget_usd=float(funding) if funding else 0,
        deliverables=[],
        goals=goals,
        constraints=[],
        completion_percent=50,
        has_demo=False,
    )
    
    project = Project(
        id="frontend-draft",
        created_at=datetime.now(timezone.utc),
        title=payload.get("description", "Startup")[:60] or "Startup Project",
        description=description,
        team_name="Frontend Team",
        metrics=metrics,
    )
    
    sponsors = store.list_sponsors()
    if not sponsors:
        raise HTTPException(status_code=503, detail="No sponsors configured")
    
    req = MatchRequest(user_context=f"{industry} {stage} {country} {description}", top_k=payload.get("top_k", 50))
    result = matching.run_matching(project, sponsors, req)
    
    matches = []
    for m in result.matches:
        # Find the opportunity
        opp = None
        for s in sponsors:
            if s.id == m.sponsor.id:
                opp = {
                    "id": s.id,
                    "name": s.name,
                    "provider": s.name,
                    "category": "Funding",
                    "description": s.description or s.tagline,
                    "countries": ["Malaysia", "ASEAN-wide"],
                    "targetStages": ["Pre-seed", "Seed", "Growth"],
                    "targetIndustries": s.focus_domains,
                    "goals": s.keywords,
                    "eligibility": s.requirements,
                    "applicationDeadline": None,
                    "deadlineNote": f"Deadline: {s.deadline_hours} hours",
                    "dataStatus": "demo",
                    "sourceUrl": None,
                    "lastVerifiedDate": None,
                }
                break
        matches.append({
            "opportunity": opp,
            "percent": int(m.score * 1.0),  # frontend expects percent out of 100
            "score": m.score,
            "label": "Match",
            "reasons": m.reasons,
            "missing": m.gaps,
        })
    
    return {"matches": matches, "summary": result.summary, "warning": result.warning}
