"""Rule-based matching for the startup-owner side of the gateway.

This is deliberately deterministic: no LLM, no external calls, no eligibility
decision. The browser does not score anything; both the HTML frontend and any
other client ask this module so that there is one implementation.

Scoring (maximum 9 points):
    country    exact match = 3, "ASEAN-wide" = 2
    industry   exact/related match = 2, "Any" = 1, unknown = 0
    stage      exact/related match = 2, "Any" = 1, unknown = 0
    goals      1 point per shared goal, capped at 2

The new profile form uses slightly different labels from the original demo
records (for example "Healthcare" vs "HealthTech"). The alias tables below keep
those older records matchable without rewriting the JSON data.

Verification status (dataStatus) is intentionally NOT scored. It is shown on
the card for transparency only.
"""

from typing import List, Optional, Set, Tuple

from .models import (
    Opportunity,
    OpportunityMatchRequest,
    OpportunityMatchResponse,
    OpportunityMatchResult,
)

MAX_SCORE = 3 + 2 + 2 + 2  # 9

CRITERIA = [
    "Country coverage",
    "Industry focus",
    "Startup stage",
    "Shared goals",
]

# Profile label -> labels used by older records that mean the same thing.
INDUSTRY_ALIASES = {
    "Fintech": {"Fintech"},
    "Artificial Intelligence": {"Artificial Intelligence", "SaaS / Digital", "DeepTech"},
    "Software / SaaS": {"Software / SaaS", "SaaS / Digital"},
    "Climate / Clean Energy": {"Climate / Clean Energy", "Climate / GreenTech"},
    "Healthcare": {"Healthcare", "HealthTech"},
    "Education": {"Education", "EdTech"},
    "Agriculture / Food": {"Agriculture / Food", "AgriFood"},
    "E-commerce / Retail": {"E-commerce / Retail", "E-commerce", "Retail"},
    "Logistics / Mobility": {"Logistics / Mobility", "Logistics", "Mobility"},
    "Manufacturing": {"Manufacturing"},
    "Other": {"Other"},
}

STAGE_ALIASES = {
    "Idea": {"Idea"},
    "Pre-seed": {"Pre-seed"},
    "Seed": {"Seed"},
    "Series A": {"Series A"},
    "Series B+": {"Series B+"},
    "Growth / Established business": {
        "Growth / Established business",
        "Growth",
    },
}

GOAL_ALIASES = {
    "Funding": {"Funding"},
    "Mentorship": {"Mentorship"},
    "Market access": {"Market access"},
    "Partnership": {"Partnership"},
    "Incubation / Workspace": {"Incubation / Workspace", "Incubation & workspace"},
    "Talent / Hiring": {"Talent / Hiring", "Talent & hiring"},
    "Regulatory guidance": {"Regulatory guidance"},
}


def _accepted_labels(value: str, table: dict) -> Set[str]:
    return table.get(value, {value})


def _country_points(
    country: str, countries: List[str]
) -> Tuple[int, Optional[str]]:
    if not country:
        return 0, None
    if country == "ASEAN-wide":
        if "ASEAN-wide" in countries:
            return 3, "You selected ASEAN-wide and this record is region-wide."
        return 2, (
            "You selected ASEAN-wide; this record covers "
            f"{', '.join(countries)}."
        )
    if country in countries:
        return 3, f"Covers your country ({country})."
    if "ASEAN-wide" in countries:
        return 2, "Listed as ASEAN-wide, so your country is in scope."
    return 0, None


def _industry_points(
    industry: str, target_industries: Optional[List[str]]
) -> Tuple[int, Optional[str]]:
    if not industry or target_industries is None:
        return 0, None
    if industry in target_industries:
        return 2, f"Focused on your industry ({industry})."
    if _accepted_labels(industry, INDUSTRY_ALIASES) & set(target_industries):
        return 2, (
            f"Focused on a related industry ({industry}) using the older "
            "record label."
        )
    if "Any" in target_industries:
        return 1, "Open to any industry."
    return 0, None


def _stage_points(
    stage: str, target_stages: Optional[List[str]]
) -> Tuple[int, Optional[str]]:
    if not stage or target_stages is None:
        return 0, None
    if stage in target_stages:
        return 2, f"Intended for {stage} companies."
    if _accepted_labels(stage, STAGE_ALIASES) & set(target_stages):
        return 2, f"Intended for a stage that includes {stage}."
    if "Any" in target_stages:
        return 1, "Open to any company stage."
    return 0, None


def _shared_goals(
    opportunity_goals: List[str], profile_goals: List[str]
) -> List[str]:
    accepted: Set[str] = set()
    for goal in profile_goals:
        accepted |= _accepted_labels(goal, GOAL_ALIASES)
    return [goal for goal in opportunity_goals if goal in accepted]


def score_opportunity(
    opportunity: Opportunity, profile: OpportunityMatchRequest
) -> Tuple[float, int, str, List[str]]:
    """Return (raw score, percentage, label, plain-language reasons)."""
    score = 0
    reasons: List[str] = []

    country_score, country_reason = _country_points(
        profile.country, opportunity.countries
    )
    score += country_score
    if country_reason:
        reasons.append(country_reason)

    industry_score, industry_reason = _industry_points(
        profile.industry, opportunity.targetIndustries
    )
    score += industry_score
    if industry_reason:
        reasons.append(industry_reason)

    stage_score, stage_reason = _stage_points(
        profile.stage, opportunity.targetStages
    )
    score += stage_score
    if stage_reason:
        reasons.append(stage_reason)

    shared_goals = _shared_goals(opportunity.goals, profile.goals)
    if shared_goals:
        score += min(len(shared_goals), 2)
        reasons.append(f"Matches your goal: {', '.join(shared_goals)}.")

    if not reasons:
        reasons.append(
            "No direct match with the details you entered - shown only as a record in the list."
        )

    percent = round((score / MAX_SCORE) * 100)
    return float(score), percent, match_label(percent), reasons


def match_label(percent: int) -> str:
    if percent >= 70:
        return "Strong match"
    if percent >= 40:
        return "Possible match"
    if percent > 0:
        return "Weak match"
    return "No direct match"


def _specificity(opportunity: Opportunity, profile: OpportunityMatchRequest) -> int:
    """Prefer exact country/industry/stage hits over wildcard hits on a tie.

    Two records can both score 6/9 while one is an exact-country match and the
    other is ASEAN-wide. The exact match is more useful to show first.
    """
    value = 0
    if profile.country and profile.country in opportunity.countries:
        value += 3
    if (
        profile.industry
        and opportunity.targetIndustries is not None
        and profile.industry in opportunity.targetIndustries
    ):
        value += 2
    if (
        profile.stage
        and opportunity.targetStages is not None
        and profile.stage in opportunity.targetStages
    ):
        value += 2
    value += len(set(profile.goals) & set(opportunity.goals))
    return value


def run_matching(
    opportunities: List[Opportunity], profile: OpportunityMatchRequest
) -> OpportunityMatchResponse:
    ranked: List[OpportunityMatchResult] = []
    for opportunity in opportunities:
        score, percent, label, reasons = score_opportunity(opportunity, profile)
        ranked.append(
            OpportunityMatchResult(
                opportunity=opportunity,
                score=score,
                percent=percent,
                label=label,
                reasons=reasons,
            )
        )

    # Highest score first, then the most specific match, then alphabetical.
    ranked.sort(
        key=lambda item: (
            -item.score,
            -_specificity(item.opportunity, profile),
            item.opportunity.name,
        )
    )
    matches = ranked[: profile.top_k]

    summary = (
        f"Ranked {len(matches)} of {len(opportunities)} opportunities with "
        "fixed matching rules. Scores describe fit only, not eligibility, and "
        "your funding amount and description are not scored because these demo "
        "records do not publish funding ranges."
    )
    return OpportunityMatchResponse(
        engine="rules",
        model="rules-v1",
        profile=profile,
        matches=matches,
        criteria=CRITERIA,
        summary=summary,
    )
