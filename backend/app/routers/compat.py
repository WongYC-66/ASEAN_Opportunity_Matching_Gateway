from typing import List

from fastapi import APIRouter

from .. import store

router = APIRouter(tags=["compatibility"])


@router.get("/opportunities")
def list_opportunities():
    sponsors = store.list_sponsors()
    opportunities = []
    for sponsor in sponsors:
        opportunities.append(
            {
                "id": sponsor.id,
                "name": sponsor.name,
                "provider": sponsor.name,
                "category": "Funding",
                "description": sponsor.description or sponsor.tagline,
                "countries": ["Malaysia", "ASEAN-wide"],
                "targetStages": ["Pre-seed", "Seed", "Growth"],
                "targetIndustries": sponsor.focus_domains,
                "goals": sponsor.keywords,
                "eligibility": sponsor.requirements,
                "applicationDeadline": None,
                "deadlineNote": f"Deadline: {sponsor.deadline_hours} hours",
                "dataStatus": "demo",
                "sourceUrl": None,
                "lastVerifiedDate": None,
                "prize": sponsor.prize,
                "track_name": sponsor.track_name,
            }
        )
    return opportunities


@router.get("/startups")
def list_startups():
    projects = store.list_projects()
    startups = []
    for project in projects:
        m = project.metrics
        startups.append(
            {
                "id": project.id,
                "name": project.title,
                "description": project.description,
                "country": "Malaysia",
                "industry": m.domains[0].title() if m.domains else "Other",
                "stage": "Seed" if m.completion_percent < 50 else "Growth",
                "revenueStatus": None,
                "fundingSought": m.budget_usd,
                "fundingCurrency": "USD",
                "strategyTags": m.goals,
                "businessModel": ", ".join(m.deliverables) if m.deliverables else None,
                "dataStatus": "demo",
                "sourceUrl": None,
                "lastVerifiedDate": None,
                "team_name": project.team_name,
                "tech_stack": m.tech_stack,
            }
        )
    return startups
