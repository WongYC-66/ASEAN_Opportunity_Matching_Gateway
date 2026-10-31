"""Improved rule-based matching for startup owners (opportunities/programmes).
"""
from typing import List, Optional, Set, Tuple

from .models import (
    Opportunity,
    OpportunityMatchRequest,
    OpportunityMatchResponse,
    OpportunityMatchResult,
)

MAX_SCORE = 100

CRITERIA = [
    "Country compatibility",
    "Industry compatibility",
    "Startup stage compatibility",
    "Goal compatibility",
    "Funding amount compatibility",
]

INDUSTRY_ALIASES = {
    "Fintech": {"Fintech"},
    "Artificial Intelligence": {"Artificial Intelligence", "AI", "DeepTech"},
    "Software / SaaS": {"Software / SaaS", "SaaS / Digital", "Software", "SaaS"},
    "Climate / Clean Energy": {"Climate / Clean Energy", "Climate / GreenTech", "Clean Energy", "GreenTech"},
    "Healthcare": {"Healthcare", "HealthTech"},
    "Education": {"Education", "EdTech"},
    "Agriculture / Food": {"Agriculture / Food", "AgriFood", "Agriculture"},
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
    "Growth / Established business": {"Growth / Established business", "Growth", "Established business"},
}

GOAL_ALIASES = {
    "Funding": {"Funding"},
    "Mentorship": {"Mentorship"},
    "Market access": {"Market access"},
    "Partnership": {"Partnership"},
    "Incubation / Workspace": {"Incubation / Workspace", "Incubation & workspace", "Incubation", "Workspace"},
    "Talent / Hiring": {"Talent / Hiring", "Talent & hiring", "Talent", "Hiring"},
    "Regulatory guidance": {"Regulatory guidance"},
}


def _normalize(s: str) -> str:
    return (s or "").strip()


def _accepted_labels(value: str, table: dict) -> Set[str]:
    if not value:
        return set()
    return table.get(value, {value})


def _country_compatible(startup_country: str, opp_countries: List[str]) -> Tuple[bool, str, str]:
    if not startup_country:
        return True, "Country not specified", "unknown"
    if not opp_countries:
        return True, "Opportunity countries not specified", "unknown"
    opp_countries_norm = [_normalize(c) for c in opp_countries]
    if startup_country == "ASEAN-wide":
        return True, "Startup operates ASEAN-wide", "broad"
    if startup_country in opp_countries_norm:
        return True, f"Exact country match ({startup_country})", "exact"
    if "ASEAN-wide" in opp_countries_norm:
        return True, f"Opportunity is ASEAN-wide, covers {startup_country}", "broad"
    return False, f"Country mismatch: startup in {startup_country}, opportunity in {', '.join(opp_countries)}", "mismatch"


def _industry_compatible(startup_industry: str, target_industries: Optional[List[str]]) -> Tuple[bool, str, str]:
    if not startup_industry:
        return True, "Industry not specified", "unknown"
    if target_industries is None or len(target_industries) == 0:
        return True, "Industry not specified in opportunity", "unknown"
    target_norm = [_normalize(t) for t in target_industries]
    if "Any" in target_norm:
        return True, "Opportunity open to any industry", "broad"
    if startup_industry in target_norm:
        return True, f"Exact industry match ({startup_industry})", "exact"
    accepted = _accepted_labels(startup_industry, INDUSTRY_ALIASES)
    if accepted & set(target_norm):
        return True, f"Related industry match ({startup_industry})", "broad"
    return False, f"Industry mismatch: startup in {startup_industry}, opportunity targets {', '.join(target_industries)}", "mismatch"


def _stage_compatible(startup_stage: str, target_stages: Optional[List[str]]) -> Tuple[bool, str, str]:
    if not startup_stage:
        return True, "Stage not specified", "unknown"
    if target_stages is None or len(target_stages) == 0:
        return True, "Stage not specified in opportunity", "unknown"
    target_norm = [_normalize(t) for t in target_stages]
    if "Any" in target_norm:
        return True, "Opportunity open to any stage", "broad"
    if startup_stage in target_norm:
        return True, f"Exact stage match ({startup_stage})", "exact"
    accepted = _accepted_labels(startup_stage, STAGE_ALIASES)
    if accepted & set(target_norm):
        return True, f"Compatible stage match ({startup_stage})", "broad"
    return False, f"Stage mismatch: startup at {startup_stage}, opportunity targets {', '.join(target_stages)}", "mismatch"


def _goals_compatible(opportunity_goals: List[str], profile_goals: List[str]) -> Tuple[float, str, str]:
    if not profile_goals:
        return 0, "No goals specified", "unknown"
    if not opportunity_goals:
        return 0, "Opportunity goals not specified", "unknown"
    accepted_set: Set[str] = set()
    for goal in profile_goals:
        accepted_set |= _accepted_labels(goal, GOAL_ALIASES)
    shared = [goal for goal in opportunity_goals if goal in accepted_set]
    if shared:
        score = min(len(shared) * 0.5, 1.0)
        return score, f"Matches goals: {', '.join(shared)}", "exact" if len(shared) == len([g for g in profile_goals if g in accepted_set]) else "broad"
    return 0, f"No overlap in goals (need: {', '.join(profile_goals)})", "mismatch"


def _funding_compatible(profile: OpportunityMatchRequest, opportunity: Opportunity) -> Tuple[float, str, str]:
    if profile.fundingAmount is None:
        return 0, "Funding amount not specified", "unknown"
    min_f = getattr(opportunity, 'minFundingAmount', None)
    max_f = getattr(opportunity, 'maxFundingAmount', None)
    opp_currency = getattr(opportunity, 'fundingCurrency', None)
    if min_f is None and max_f is None:
        return 0, "Opportunity funding range not specified", "unknown"
    if opp_currency and profile.fundingCurrency and opp_currency != profile.fundingCurrency:
        return 0, f"Currency mismatch (opportunity: {opp_currency}, startup: {profile.fundingCurrency}) - no conversion applied", "unknown"
    curr = opp_currency or profile.fundingCurrency or "USD"
    if min_f is not None and max_f is not None:
        if profile.fundingAmount < min_f or profile.fundingAmount > max_f:
            return -1, f"Amount outside range {min_f}-{max_f} {curr}", "mismatch"
        return 1.0, f"Amount within range {min_f}-{max_f} {curr}", "exact"
    elif min_f is not None:
        if profile.fundingAmount < min_f:
            return -1, f"Amount below minimum {min_f} {curr}", "mismatch"
        return 0.5, f"Amount meets minimum {min_f} {curr}", "broad"
    elif max_f is not None:
        if profile.fundingAmount > max_f:
            return -1, f"Amount above maximum {max_f} {curr}", "mismatch"
        return 0.5, f"Amount within maximum {max_f} {curr}", "broad"
    return 0, "Cannot assess funding compatibility", "unknown"


def score_opportunity(
    opportunity: Opportunity, profile: OpportunityMatchRequest
) -> Tuple[float, int, str, List[str], List[str], List[str], List[str]]:
    total_score = 0.0
    max_possible = 0.0
    reasons: List[str] = []
    matched: List[str] = []
    unmatched: List[str] = []
    unknown: List[str] = []
    
    # Country (25%)
    country_ok, country_reason, country_status = _country_compatible(profile.country, opportunity.countries)
    max_possible += 25
    if profile.country:
        if country_ok and country_status != "unknown":
            if country_status == "exact":
                total_score += 25
                matched.append("country")
            elif country_status == "broad":
                total_score += 18
                matched.append("country")
            reasons.append(country_reason)
        elif country_status == "mismatch":
            unmatched.append("country")
            reasons.append(country_reason)
        elif country_status == "unknown":
            unknown.append("country")
            reasons.append(country_reason)
    else:
        unknown.append("country")
    
    # Industry (25%)
    industry_ok, industry_reason, industry_status = _industry_compatible(profile.industry, opportunity.targetIndustries)
    max_possible += 25
    if profile.industry:
        if industry_ok and industry_status != "unknown":
            if industry_status == "exact":
                total_score += 25
                matched.append("industry")
            elif industry_status == "broad":
                total_score += 15
                matched.append("industry")
            reasons.append(industry_reason)
        elif industry_status == "mismatch":
            unmatched.append("industry")
            reasons.append(industry_reason)
        elif industry_status == "unknown":
            unknown.append("industry")
            reasons.append(industry_reason)
    else:
        unknown.append("industry")
    
    # Stage (20%)
    stage_ok, stage_reason, stage_status = _stage_compatible(profile.stage, opportunity.targetStages)
    max_possible += 20
    if profile.stage:
        if stage_ok and stage_status != "unknown":
            if stage_status == "exact":
                total_score += 20
                matched.append("startupStage")
            elif stage_status == "broad":
                total_score += 12
                matched.append("startupStage")
            reasons.append(stage_reason)
        elif stage_status == "mismatch":
            unmatched.append("startupStage")
            reasons.append(stage_reason)
        elif stage_status == "unknown":
            unknown.append("startupStage")
            reasons.append(stage_reason)
    else:
        unknown.append("startupStage")
    
    # Goals (20%) - OR logic
    if profile.goals:
        max_possible += 20
        goal_score, goal_reason, goal_status = _goals_compatible(opportunity.goals, profile.goals)
        if goal_score > 0:
            total_score += goal_score * 20
            matched.append("goals")
        elif goal_status == "mismatch":
            unmatched.append("goals")
        elif goal_status == "unknown":
            unknown.append("goals")
        if goal_reason and goal_reason != "No goals specified":
            reasons.append(goal_reason)
    else:
        unknown.append("goals")
    
    # Funding (10%)
    if profile.fundingAmount is not None:
        max_possible += 10
        fund_score, fund_reason, fund_status = _funding_compatible(profile, opportunity)
        if fund_score > 0:
            total_score += fund_score * 10
            matched.append("funding")
        elif fund_score == -1:
            unmatched.append("funding")
        elif fund_status == "unknown":
            unknown.append("funding")
        if fund_reason and fund_reason != "Funding amount not specified":
            reasons.append(fund_reason)
    else:
        unknown.append("funding")
    
    if not reasons:
        reasons.append("Limited information provided for matching.")
    
    if max_possible > 0:
        percent = round((total_score / max_possible) * 100)
    else:
        percent = 0
    
    percent = max(0, min(100, percent))
    return float(total_score), percent, match_label(percent), reasons, matched, unmatched, unknown


def match_label(percent: int) -> str:
    if percent >= 80:
        return "Strong match"
    if percent >= 50:
        return "Possible match"
    if percent > 0:
        return "Weak match"
    return "No match on assessed criteria"


def _specificity(opportunity, profile) -> int:
    value = 0
    if profile.country and opportunity.countries and profile.country in opportunity.countries:
        value += 3
    if profile.industry and opportunity.targetIndustries and profile.industry in opportunity.targetIndustries:
        value += 2
    if profile.stage and opportunity.targetStages and profile.stage in opportunity.targetStages:
        value += 2
    try:
        value += len(set(profile.goals) & set(opportunity.goals or []))
    except Exception:
        pass
    return value


def run_matching(
    opportunities: List[Opportunity], profile: OpportunityMatchRequest
) -> OpportunityMatchResponse:
    ranked: List[OpportunityMatchResult] = []
    for opportunity in opportunities:
        score, percent, label, reasons, matched, unmatched, unknown = score_opportunity(opportunity, profile)
        ranked.append(
            OpportunityMatchResult(
                opportunity=opportunity,
                score=score,
                percent=percent,
                label=label,
                reasons=reasons,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.percent,
            -_specificity(item.opportunity, profile),
            item.opportunity.name,
        )
    )
    # Filter out results below 50% or with no meaningful score/value
    filtered = []
    for item in ranked:
        pct = item.percent
        if pct is None:
            continue
        try:
            fpct = float(pct)
            if fpct < 50.0 or fpct <= 0.5 or fpct == 0 or fpct == 0.0:
                continue
        except Exception:
            continue
        if item.label in ("No match on assessed criteria", "No match", "No direct match"):
            continue
        filtered.append(item)
    matches = filtered[: profile.top_k]

    summary = (
        f"Ranked {len(matches)} of {len(opportunities)} opportunities with "
        "fixed matching rules. Scores describe fit only, not eligibility."
    )
    return OpportunityMatchResponse(
        engine="rules",
        model="rules-v1",
        profile=profile,
        matches=matches,
        criteria=CRITERIA,
        summary=summary,
    )
