from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

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
