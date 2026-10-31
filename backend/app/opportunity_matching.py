"""Rule-based matching for the ASEAN Opportunity Finder.

This is deliberately deterministic: no LLM, no external calls, no eligibility
decision. The browser used to score records itself; the integrated app now asks
this module so that both sides share one implementation.

Scoring (maximum 9 points):
    country    exact match = 3, "ASEAN-wide" = 2
    industry   exact match = 2, "Any" = 1, null/unknown = 0
    stage      exact match = 2, "Any" = 1, null/unknown = 0
    goals      1 point per shared goal, capped at 2

Verification status (dataStatus) is intentionally NOT scored. It is shown on
the card for transparency only.
"""

from typing import List, Tuple

from .models import (
    Opportunity,
    OpportunityMatchRequest,
    OpportunityMatchResponse,
    OpportunityMatchResult,
)

MAX_SCORE = 3 + 2 + 2 + 2  # 9


def score_opportunity(
    opportunity: Opportunity, profile: OpportunityMatchRequest
) -> Tuple[float, int, str, List[str]]:
    """Return (raw score, percentage, label, plain-language reasons)."""
    score = 0
    reasons: List[str] = []

    if profile.country:
        if profile.country in opportunity.countries:
            score += 3
            reasons.append(f"Covers your country ({profile.country}).")
        elif "ASEAN-wide" in opportunity.countries:
            score += 2
            reasons.append("Listed as ASEAN-wide, so your country is in scope.")

    if profile.industry and opportunity.targetIndustries is not None:
        if profile.industry in opportunity.targetIndustries:
            score += 2
            reasons.append(f"Focused on your industry ({profile.industry}).")
        elif "Any" in opportunity.targetIndustries:
            score += 1
            reasons.append("Open to any industry.")

    if profile.stage and opportunity.targetStages is not None:
        if profile.stage in opportunity.targetStages:
            score += 2
            reasons.append(f"Intended for {profile.stage} companies.")
        elif "Any" in opportunity.targetStages:
            score += 1
            reasons.append("Open to any company stage.")

    shared_goals = [
        goal for goal in opportunity.goals if goal in set(profile.goals)
    ]
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
        "fixed matching rules. Scores describe fit only, not eligibility."
    )
    return OpportunityMatchResponse(
        engine="rules",
        model="rules-v1",
        profile=profile,
        matches=matches,
        summary=summary,
    )
