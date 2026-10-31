"""Rule-based investor matching for illustrative startup profiles.

Deterministic and explainable: no LLM, no external calls, no claim that a match
is an introduction, an offer, or due diligence.

Weights (only applied when both sides have enough information):
    geography  30   startup country vs the investor's target markets
    industry   25   startup industry vs the investor's target industries
    stage      20   startup stage vs the investor's target stages
    strategy   15   overlap between startup strategy tags and investor strategies
    ticket     10   startup funding requirement inside the investor's ticket range

The percentage is earned points divided by the points that could actually be
assessed, so a startup is never penalised because its record is incomplete.
Missing information is returned in ``missing`` instead of reducing the score.
Verification status (dataStatus) is never scored.
"""

from typing import List, Optional, Tuple

from .models import InvestorMatchRequest, Startup, StartupMatchResult, StartupMatchResponse

CRITERIA = [
    "Geography (30 points)",
    "Industry (25 points)",
    "Startup stage (20 points)",
    "Investment strategy (15 points)",
    "Ticket-size compatibility (10 points)",
]

Assessment = Tuple[int, int, Optional[str], Optional[str]]


def _money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.0f}"


def _geography(startup: Startup, profile: InvestorMatchRequest) -> Assessment:
    if not profile.countries:
        return (
            0,
            0,
            None,
            "Preferred geography was not provided, so geography was not assessed.",
        )
    if startup.country == "ASEAN-wide" or "ASEAN-wide" in profile.countries:
        return (
            30,
            30,
            f"Operates in {startup.country}, which falls within the markets you selected.",
            None,
        )
    if startup.country in profile.countries:
        return (
            30,
            30,
            f"Operates in one of your target markets ({startup.country}).",
            None,
        )
    return (
        0,
        30,
        f"Operates in {startup.country}, outside the markets you selected.",
        None,
    )


def _industry(startup: Startup, profile: InvestorMatchRequest) -> Assessment:
    if not profile.industries:
        return (
            0,
            0,
            None,
            "Preferred industries were not provided, so industry was not assessed.",
        )
    if startup.industry in profile.industries:
        return (
            25,
            25,
            f"Industry matches your focus ({startup.industry}).",
            None,
        )
    return (
        0,
        25,
        f"Industry ({startup.industry}) is outside your selected industries.",
        None,
    )


def _stage(startup: Startup, profile: InvestorMatchRequest) -> Assessment:
    if not profile.stages:
        return (
            0,
            0,
            None,
            "Preferred stages were not provided, so stage was not assessed.",
        )
    if startup.stage in profile.stages:
        return (
            20,
            20,
            f"Startup stage matches your preference ({startup.stage}).",
            None,
        )
    return (
        0,
        20,
        f"Stage ({startup.stage}) is outside your selected stages.",
        None,
    )


def _strategy(startup: Startup, profile: InvestorMatchRequest) -> Assessment:
    if not profile.strategies:
        return (
            0,
            0,
            None,
            "No investment strategies selected, so strategy fit was not assessed.",
        )
    if not startup.strategyTags:
        return (
            0,
            0,
            None,
            "Strategy tags are not recorded for this startup, so strategy fit "
            "could not be assessed.",
        )
    shared = [tag for tag in startup.strategyTags if tag in profile.strategies]
    if shared:
        return (
            15,
            15,
            f"Recorded strategy overlap: {', '.join(shared)}.",
            None,
        )
    return (
        0,
        15,
        "Recorded strategy tags do not overlap your selected strategies.",
        None,
    )


def _ticket(startup: Startup, profile: InvestorMatchRequest) -> Assessment:
    if profile.ticketMin is None and profile.ticketMax is None:
        return (
            0,
            0,
            None,
            "No ticket range was set, so ticket-size compatibility was not assessed.",
        )
    if startup.fundingSought is None or startup.fundingCurrency is None:
        return (
            0,
            0,
            None,
            "The startup's funding requirement is not recorded, so ticket-size "
            "compatibility could not be assessed.",
        )
    if startup.fundingCurrency != profile.currency:
        return (
            0,
            0,
            None,
            f"Startup seeks {startup.fundingCurrency} but your ticket is in "
            f"{profile.currency}; no currency conversion is applied, so "
            "ticket-size compatibility could not be assessed.",
        )

    low = profile.ticketMin if profile.ticketMin is not None else 0
    high = profile.ticketMax if profile.ticketMax is not None else float("inf")
    sought = startup.fundingSought
    currency = startup.fundingCurrency
    if low <= sought <= high:
        if high == float("inf"):
            range_text = f"{_money(low, currency)} or more"
        else:
            range_text = f"{_money(low, currency)} to {_money(high, currency)}"
        return (
            10,
            10,
            f"Seeks {_money(sought, currency)}, inside your {range_text} range.",
            None,
        )
    return (
        0,
        10,
        f"Seeks {_money(sought, currency)}, outside the ticket range you set.",
        None,
    )


def match_label(percent: int) -> str:
    if percent >= 80:
        return "Strong match"
    if percent >= 50:
        return "Possible match"
    if percent > 0:
        return "Weak match"
    return "No match on assessed criteria"


def score_startup(
    startup: Startup, profile: InvestorMatchRequest
) -> Tuple[float, int, str, List[str], List[str], List[str]]:
    """Return (score, percent, label, reasons, missing, assessed)."""
    reasons: List[str] = []
    missing: List[str] = []
    assessed: List[str] = []
    earned = 0
    possible = 0

    for name, assessment in (
        ("Geography", _geography(startup, profile)),
        ("Industry", _industry(startup, profile)),
        ("Stage", _stage(startup, profile)),
        ("Strategy", _strategy(startup, profile)),
        ("Ticket size", _ticket(startup, profile)),
    ):
        points, available, reason, gap = assessment
        if available:
            earned += points
            possible += available
            assessed.append(name)
        if reason:
            reasons.append(reason)
        if gap:
            missing.append(gap)

    if possible:
        exact = round((earned / possible) * 100, 1)
    else:
        exact = 0.0
    percent = int(round(exact))

    if not reasons:
        reasons.append(
            "No match reason could be produced because the investor profile was empty."
        )

    return exact, percent, match_label(percent), reasons, missing, assessed


def _confidence(result: StartupMatchResult) -> int:
    return len(result.assessed)


def run_matching(
    startups: List[Startup], profile: InvestorMatchRequest
) -> StartupMatchResponse:
    ranked: List[StartupMatchResult] = []
    for startup in startups:
        score, percent, label, reasons, missing, assessed = score_startup(
            startup, profile
        )
        ranked.append(
            StartupMatchResult(
                startup=startup,
                score=score,
                percent=percent,
                label=label,
                reasons=reasons,
                missing=missing,
                assessed=assessed,
            )
        )

    # Best match first, then the record with more assessable criteria, then name.
    ranked.sort(
        key=lambda item: (-item.score, -_confidence(item), item.startup.name)
    )
    matches = ranked[: profile.top_k]

    warning = None
    if matches and all(item.startup.dataStatus == "demo" for item in matches):
        warning = (
            "Every startup shown is a fictional demo profile. Demo profiles are "
            "illustrations, not real investable businesses, and no introduction "
            "or contact has been arranged."
        )

    summary = (
        f"Ranked {len(matches)} of {len(startups)} startup profiles with fixed "
        "rules. Scores are normalised over the criteria that could be assessed "
        "(0-100) and describe fit only, not investment readiness."
    )
    return StartupMatchResponse(
        engine="rules",
        model="investor-rules-v1",
        profile=profile,
        matches=matches,
        criteria=CRITERIA,
        summary=summary,
        warning=warning,
    )
