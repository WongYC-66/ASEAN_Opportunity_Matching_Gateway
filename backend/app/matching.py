"""Sponsor <-> project matching.

Uses the configured LLM when available, otherwise (or on failure) the local
heuristic scorer. Both produce the same ranked shape for the UI.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from . import llm
from .models import MatchRequest, MatchResponse, MatchResult, Project, Sponsor

LEVELS = {"beginner": 1, "intermediate": 2, "advanced": 3}

SYSTEM_PROMPT = (
    "You are an expert hackathon sponsor-matching engine. "
    "Given one project (with structured metrics) and a list of sponsors, score "
    "how well the project fits each sponsor. Weigh technology fit, domain fit, "
    "prize track alignment, team readiness, and feasibility within the deadline. "
    "Scores must be 0-100 and discriminative (do not give everything 80+). "
    "Return ONLY valid JSON, no prose outside the JSON object."
)


def _norm(value: str) -> str:
    return value.strip().lower()


def _term_match(term: str, text: str) -> bool:
    term = _norm(term)
    return bool(term) and term in text


def _project_blob(project: Project, user_context: str) -> str:
    metrics = project.metrics
    parts = [
        project.title,
        project.description,
        project.team_name,
        " ".join(metrics.tech_stack),
        " ".join(metrics.domains),
        " ".join(metrics.team_skills),
        " ".join(metrics.deliverables),
        " ".join(metrics.goals),
        " ".join(metrics.constraints),
        user_context,
    ]
    return _norm(" | ".join(part for part in parts if part))


def _count_hits(needles: List[str], text: str) -> Tuple[int, List[str]]:
    matched = []
    for needle in needles:
        if _term_match(needle, text):
            matched.append(needle)
    return len(matched), matched


def heuristic_score(
    project: Project, sponsor: Sponsor, user_context: str
) -> MatchResult:
    text = _project_blob(project, user_context)
    metrics = project.metrics
    reasons: List[str] = []
    gaps: List[str] = []
    score = 0.0

    # --- Technology fit (35) ---
    if sponsor.preferred_tech:
        hits, matched = _count_hits(sponsor.preferred_tech, text)
        ratio = hits / len(sponsor.preferred_tech)
        score += ratio * 35
        if matched:
            reasons.append(
                f"Stack overlaps {hits}/{len(sponsor.preferred_tech)} preferred "
                f"technologies ({', '.join(matched[:4])})."
            )
        missing = [tech for tech in sponsor.preferred_tech if tech not in matched]
        if missing:
            gaps.append(f"Could add {', '.join(missing[:3])} to the stack.")
    else:
        score += 20
        reasons.append("Sponsor has no strict technology list.")

    # --- Domain fit (25) ---
    if sponsor.focus_domains:
        hits, matched = _count_hits(sponsor.focus_domains, text)
        score += (hits / len(sponsor.focus_domains)) * 25
        if matched:
            reasons.append(f"Aligned domains: {', '.join(matched)}.")
        else:
            gaps.append(
                f"Story not connected to {', '.join(sponsor.focus_domains[:2])} yet."
            )
    else:
        score += 12

    # --- Prize track / judging fit (15) ---
    track_terms = [sponsor.track_name] + sponsor.keywords + sponsor.judging_criteria
    hits, matched = _count_hits([term for term in track_terms if term], text)
    if track_terms:
        score += min(1.0, hits / max(2, len(track_terms) * 0.4)) * 15
    if matched:
        reasons.append(f"Speaks to the '{sponsor.track_name}' track.")

    # --- Team readiness (15) ---
    readiness = 0.0
    project_level = LEVELS.get(_norm(metrics.experience_level), 2)
    sponsor_level = LEVELS.get(_norm(sponsor.preferred_experience), 2)
    readiness += 1.0 if project_level >= sponsor_level else 0.6
    if sponsor.min_team_size <= metrics.team_size <= sponsor.max_team_size:
        readiness += 1.0
        reasons.append(f"Team size {metrics.team_size} fits the sponsor's range.")
    else:
        readiness += 0.2
        gaps.append(
            f"Team size {metrics.team_size} is outside "
            f"{sponsor.min_team_size}-{sponsor.max_team_size}."
        )
    readiness += metrics.completion_percent / 100
    if metrics.has_demo:
        readiness += 0.4
        reasons.append("A working demo is ready for judging.")
    score += min(1.0, readiness / 3.4) * 15

    # --- Constraints / feasibility (10) ---
    constraint_score = 0.0
    if sponsor.requires_open_source:
        if metrics.open_source:
            constraint_score += 1
            reasons.append("Meets the open-source requirement.")
        else:
            gaps.append("Sponsor requires an open-source submission.")
    else:
        constraint_score += 1
    if sponsor.budget_cap_usd and metrics.budget_usd > sponsor.budget_cap_usd:
        gaps.append(
            f"Budget ${metrics.budget_usd:g} exceeds the ${sponsor.budget_cap_usd:g} cap."
        )
    else:
        constraint_score += 1
    if metrics.duration_hours > sponsor.deadline_hours:
        gaps.append(
            f"Plan needs {metrics.duration_hours}h vs {sponsor.deadline_hours}h deadline."
        )
    else:
        constraint_score += 1
    score += (constraint_score / 3) * 10

    if not reasons:
        reasons.append("General fit based on the submitted description.")
    return MatchResult(
        sponsor=sponsor,
        score=round(min(100.0, max(0.0, score)), 1),
        reasons=reasons[:4],
        gaps=gaps[:3],
    )


def heuristic_rank(
    project: Project, sponsors: List[Sponsor], user_context: str
) -> List[MatchResult]:
    results = [heuristic_score(project, sponsor, user_context) for sponsor in sponsors]
    results.sort(key=lambda item: item.score, reverse=True)
    return results


def _build_user_prompt(
    project: Project,
    sponsors: List[Sponsor],
    user_context: str,
    top_k: int,
) -> str:
    sponsor_payload = [
        {
            "id": sponsor.id,
            "name": sponsor.name,
            "focus_domains": sponsor.focus_domains,
            "preferred_tech": sponsor.preferred_tech,
            "track_name": sponsor.track_name,
            "prize": sponsor.prize,
            "judging_criteria": sponsor.judging_criteria,
            "requirements": sponsor.requirements,
            "preferred_experience": sponsor.preferred_experience,
            "team_size_range": [sponsor.min_team_size, sponsor.max_team_size],
            "requires_open_source": sponsor.requires_open_source,
            "budget_cap_usd": sponsor.budget_cap_usd,
            "deadline_hours": sponsor.deadline_hours,
            "keywords": sponsor.keywords,
        }
        for sponsor in sponsors
    ]
    return (
        "PROJECT\n"
        f"{json.dumps(project.model_dump(mode='json'), ensure_ascii=False)}\n\n"
        "ADDITIONAL USER CONTEXT\n"
        f"{user_context or '(none)'}\n\n"
        "SPONSORS\n"
        f"{json.dumps(sponsor_payload, ensure_ascii=False)}\n\n"
        "Return JSON with this exact shape:\n"
        '{"summary": "one or two sentences", "matches": ['
        '{"sponsor_id": "<id>", "score": <0-100>, "reasons": ["..."], '
        '"gaps": ["..."]}]}\n'
        f"Return exactly {min(top_k, len(sponsors))} matches sorted by score "
        "descending. Max 3 reasons and 2 gaps per match. Use only sponsor ids "
        "from the list."
    )


def _parse_llm_matches(
    raw: Any, sponsors: List[Sponsor], top_k: int
) -> Tuple[List[MatchResult], str]:
    if isinstance(raw, list):
        raw = {"matches": raw}
    if not isinstance(raw, dict):
        raise ValueError("LLM JSON was not an object")

    sponsor_by_id = {sponsor.id: sponsor for sponsor in sponsors}
    results: List[MatchResult] = []
    seen = set()
    for item in raw.get("matches") or []:
        if not isinstance(item, dict):
            continue
        sponsor_id = str(item.get("sponsor_id") or "")
        sponsor = sponsor_by_id.get(sponsor_id)
        if not sponsor or sponsor_id in seen:
            continue
        seen.add(sponsor_id)
        try:
            score = float(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0
        reasons = [str(reason) for reason in item.get("reasons") or [] if reason]
        gaps = [str(gap) for gap in item.get("gaps") or [] if gap]
        results.append(
            MatchResult(
                sponsor=sponsor,
                score=round(min(100.0, max(0.0, score)), 1),
                reasons=reasons[:4],
                gaps=gaps[:3],
            )
        )

    if not results:
        raise ValueError("LLM returned no usable matches")
    results.sort(key=lambda item: item.score, reverse=True)
    summary = str(raw.get("summary") or "")
    return results[:top_k], summary


def run_matching(
    project: Project,
    sponsors: List[Sponsor],
    request: MatchRequest,
) -> MatchResponse:
    top_k = min(request.top_k, len(sponsors))
    cfg = llm.get_config()
    warning: Optional[str] = None

    if cfg.available:
        try:
            raw = llm.chat_json(
                SYSTEM_PROMPT,
                _build_user_prompt(
                    project, sponsors, request.user_context, request.top_k
                ),
                cfg,
            )
            matches, summary = _parse_llm_matches(raw, sponsors, top_k)
            return MatchResponse(
                engine="llm",
                model=cfg.model,
                project=project,
                matches=matches,
                summary=summary,
            )
        except Exception as exc:  # noqa: BLE001 - fall back on any LLM failure
            warning = f"LLM matching failed ({exc}); used heuristic fallback."

    matches = heuristic_rank(project, sponsors, request.user_context)[:top_k]
    summary = (
        f"Ranked {len(matches)} sponsor(s) using the local heuristic engine."
    )
    return MatchResponse(
        engine="heuristic",
        model="builtin-heuristic",
        project=project,
        matches=matches,
        summary=summary,
        warning=warning,
    )
