from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

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
    """The startup owner profile sent by the frontend. All fields are optional."""

    country: str = Field(default="", max_length=80)
    industry: str = Field(default="", max_length=80)
    stage: str = Field(default="", max_length=80)
    goals: List[str] = Field(default_factory=list, max_length=20)
    # Collected for the user's own reference. Opportunity records do not record
    # funding ranges, so these fields are not part of the score.
    fundingAmount: Optional[float] = Field(default=None, ge=0)
    fundingCurrency: Optional[Literal["USD", "SGD", "MYR"]] = None
    description: str = Field(default="", max_length=400)
    top_k: int = Field(default=50, ge=1, le=100)

    @model_validator(mode="after")
    def _check_funding_pair(self):
        if self.fundingAmount is not None and self.fundingCurrency is None:
            raise ValueError("fundingCurrency is required when fundingAmount is set")
        if self.fundingAmount is None and self.fundingCurrency is not None:
            raise ValueError("fundingAmount is required when fundingCurrency is set")
        return self


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
    criteria: List[str] = Field(default_factory=list)
    summary: str = ""
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# Shared taxonomies for the dual-sided gateway
# ---------------------------------------------------------------------------

CURRENCIES = ("USD", "SGD", "MYR")

STARTUP_COUNTRIES = (
    "Malaysia",
    "Singapore",
    "Indonesia",
    "Thailand",
    "Vietnam",
    "Philippines",
    "Brunei",
    "Cambodia",
    "Laos",
    "Myanmar",
    "Timor-Leste",
    "ASEAN-wide",
)

STARTUP_INDUSTRIES = (
    "Fintech",
    "Artificial Intelligence",
    "Software / SaaS",
    "Climate / Clean Energy",
    "Healthcare",
    "Education",
    "Agriculture / Food",
    "E-commerce / Retail",
    "Logistics / Mobility",
    "Manufacturing",
    "Other",
)

STARTUP_STAGES = (
    "Idea",
    "Pre-seed",
    "Seed",
    "Series A",
    "Series B+",
    "Growth / Established business",
)

INVESTOR_TYPES = (
    "Angel Investor",
    "Venture Capital Fund",
    "Corporate Venture Capital",
    "Family Office",
    "Private Equity",
    "Accelerator / Incubator",
    "Strategic Corporate Investor",
    "Other",
)

INVESTOR_STRATEGIES = (
    "Early-stage growth",
    "Revenue-generating businesses",
    "Deep technology",
    "Impact / ESG",
    "Strategic partnerships",
    "Market expansion",
    "Other",
)

INVESTOR_GOALS = (
    "Discover startups",
    "Find co-investors",
    "Find co-investment opportunities",
    "Explore new ASEAN markets",
    "Find strategic investment opportunities",
    "Discover accelerator or ecosystem partnerships",
)


def _check_choices(values: List[str], allowed: tuple, label: str) -> List[str]:
    """Reject unknown values and remove duplicates while keeping the order."""
    unknown = [value for value in values if value not in allowed]
    if unknown:
        raise ValueError(f"unsupported {label}: {', '.join(unknown)}")
    return list(dict.fromkeys(values))


# ---------------------------------------------------------------------------
# Investor discovery (illustrative startup profiles)
# ---------------------------------------------------------------------------


class Startup(BaseModel):
    """One startup profile shown to investors.

    Every field is either explicitly recorded or ``null`` ("not recorded").
    The backend never generates financial metrics; values come from
    startups.json and every record is clearly marked demo or verified.
    """

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=400)
    country: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    businessModel: Optional[str] = Field(default=None, max_length=160)
    revenueStatus: Optional[Literal["Pre-revenue", "Revenue-generating"]] = None
    fundingSought: Optional[float] = Field(default=None, ge=0)
    fundingCurrency: Optional[Literal["USD", "SGD", "MYR"]] = None
    strategyTags: Optional[List[str]] = None
    dataStatus: Literal["demo", "verified"]
    sourceUrl: Optional[str] = None
    lastVerifiedDate: Optional[str] = None
    notes: str = ""

    @field_validator("country")
    @classmethod
    def _valid_country(cls, value: str) -> str:
        if value not in STARTUP_COUNTRIES:
            raise ValueError(f"unsupported country: {value}")
        return value

    @field_validator("industry")
    @classmethod
    def _valid_industry(cls, value: str) -> str:
        if value not in STARTUP_INDUSTRIES:
            raise ValueError(f"unsupported industry: {value}")
        return value

    @field_validator("stage")
    @classmethod
    def _valid_stage(cls, value: str) -> str:
        if value not in STARTUP_STAGES:
            raise ValueError(f"unsupported stage: {value}")
        return value

    @field_validator("strategyTags")
    @classmethod
    def _valid_strategy_tags(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        return _check_choices(value, INVESTOR_STRATEGIES, "strategy tag")

    @field_validator("lastVerifiedDate")
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

    @model_validator(mode="after")
    def _check_funding_pair(self):
        if self.fundingSought is not None and self.fundingCurrency is None:
            raise ValueError("fundingCurrency is required when fundingSought is set")
        if self.fundingSought is None and self.fundingCurrency is not None:
            raise ValueError("fundingSought is required when fundingCurrency is set")
        return self


class InvestorMatchRequest(BaseModel):
    """The investor profile sent by the frontend. All fields are optional."""

    investorType: str = Field(default="", max_length=80)
    countries: List[str] = Field(default_factory=list, max_length=12)
    industries: List[str] = Field(default_factory=list, max_length=11)
    stages: List[str] = Field(default_factory=list, max_length=6)
    ticketMin: Optional[float] = Field(default=None, ge=0)
    ticketMax: Optional[float] = Field(default=None, ge=0)
    currency: Literal["USD", "SGD", "MYR"] = "USD"
    strategies: List[str] = Field(default_factory=list, max_length=7)
    goals: List[str] = Field(default_factory=list, max_length=6)
    description: str = Field(default="", max_length=400)
    top_k: int = Field(default=50, ge=1, le=100)

    @field_validator("investorType")
    @classmethod
    def _valid_investor_type(cls, value: str) -> str:
        if value and value not in INVESTOR_TYPES:
            raise ValueError(f"unsupported investor type: {value}")
        return value

    @field_validator("countries")
    @classmethod
    def _valid_countries(cls, values: List[str]) -> List[str]:
        return _check_choices(values, STARTUP_COUNTRIES, "country")

    @field_validator("industries")
    @classmethod
    def _valid_industries(cls, values: List[str]) -> List[str]:
        return _check_choices(values, STARTUP_INDUSTRIES, "industry")

    @field_validator("stages")
    @classmethod
    def _valid_stages(cls, values: List[str]) -> List[str]:
        return _check_choices(values, STARTUP_STAGES, "stage")

    @field_validator("strategies")
    @classmethod
    def _valid_strategies(cls, values: List[str]) -> List[str]:
        return _check_choices(values, INVESTOR_STRATEGIES, "strategy")

    @field_validator("goals")
    @classmethod
    def _valid_goals(cls, values: List[str]) -> List[str]:
        return _check_choices(values, INVESTOR_GOALS, "goal")

    @model_validator(mode="after")
    def _check_ticket_range(self):
        if (
            self.ticketMin is not None
            and self.ticketMax is not None
            and self.ticketMin > self.ticketMax
        ):
            raise ValueError("ticketMin must be less than or equal to ticketMax")
        return self


class StartupMatchResult(BaseModel):
    startup: Startup
    score: float = Field(ge=0, le=100)
    percent: int = Field(ge=0, le=100)
    label: str
    reasons: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    assessed: List[str] = Field(default_factory=list)


class StartupMatchResponse(BaseModel):
    engine: str = "rules"
    model: str = "investor-rules-v1"
    profile: InvestorMatchRequest
    matches: List[StartupMatchResult]
    criteria: List[str] = Field(default_factory=list)
    summary: str = ""
    warning: Optional[str] = None
