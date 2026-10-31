from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Experience = str  # "beginner" | "intermediate" | "advanced"


class Metrics(BaseModel):
    """Signals the UI sends about a project and its team."""

    tech_stack: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    team_size: int = Field(default=1, ge=1, le=100)
    experience_level: Experience = "intermediate"
    team_skills: List[str] = Field(default_factory=list)
    duration_hours: int = Field(default=24, ge=1)
    open_source: bool = True
    budget_usd: float = Field(default=0, ge=0)
    deliverables: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    completion_percent: int = Field(default=0, ge=0, le=100)
    has_demo: bool = False


class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    team_name: str = Field(default="", max_length=120)
    metrics: Metrics = Field(default_factory=Metrics)


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase):
    id: str
    created_at: datetime


class Sponsor(BaseModel):
    id: str
    name: str
    tagline: str = ""
    description: str = ""
    focus_domains: List[str] = Field(default_factory=list)
    preferred_tech: List[str] = Field(default_factory=list)
    track_name: str = ""
    prize: str = ""
    judging_criteria: List[str] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    preferred_experience: Experience = "intermediate"
    min_team_size: int = 1
    max_team_size: int = 10
    requires_open_source: bool = False
    budget_cap_usd: float = 0
    deadline_hours: int = 48
    keywords: List[str] = Field(default_factory=list)


class MatchRequest(BaseModel):
    """Either reference an existing project or send an inline project draft."""

    project_id: Optional[str] = None
    project: Optional[ProjectCreate] = None
    user_context: str = Field(default="", max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)


class MatchResult(BaseModel):
    sponsor: Sponsor
    score: float = Field(ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


class MatchResponse(BaseModel):
    engine: str
    model: str = ""
    project: Project
    matches: List[MatchResult]
    summary: str = ""
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# Opportunity Finder (frontend-facing, camelCase to match the original data.js)
# ---------------------------------------------------------------------------


class Opportunity(BaseModel):
    """One opportunity record.

    Field names deliberately mirror the browser's JSON schema (camelCase) so
    the HTML/JS frontend can consume this endpoint without a mapping layer.
    ``null`` still means "not recorded"; an empty list means "none recorded".
    """

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    category: Literal["Funding", "Support", "Partnership"]
    description: str = ""
    countries: List[str] = Field(min_length=1)
    targetStages: Optional[List[str]] = None
    targetIndustries: Optional[List[str]] = None
    goals: List[str] = Field(default_factory=list)
    eligibility: Optional[List[str]] = None
    applicationDeadline: Optional[str] = None
    deadlineNote: Optional[str] = None
    dataStatus: Literal["demo", "verified"]
    sourceUrl: Optional[str] = None
    lastVerifiedDate: Optional[str] = None
    notes: str = ""

    @field_validator("applicationDeadline", "lastVerifiedDate")
    @classmethod
    def _valid_iso_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("must be a valid YYYY-MM-DD date or null") from exc
        return value

    @field_validator("sourceUrl")
    @classmethod
    def _valid_source_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("must be a full http(s) URL or null")
        return value


class OpportunityMatchRequest(BaseModel):
    """The startup profile sent by the frontend. All fields are optional."""

    country: str = Field(default="", max_length=80)
    industry: str = Field(default="", max_length=80)
    stage: str = Field(default="", max_length=80)
    goals: List[str] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=50, ge=1, le=100)


class OpportunityMatchResult(BaseModel):
    opportunity: Opportunity
    score: float = Field(ge=0, le=9)
    percent: int = Field(ge=0, le=100)
    label: str
    reasons: List[str] = Field(default_factory=list)


class OpportunityMatchResponse(BaseModel):
    engine: str = "rules"
    model: str = "rules-v1"
    profile: OpportunityMatchRequest
    matches: List[OpportunityMatchResult]
    summary: str = ""
    warning: Optional[str] = None
