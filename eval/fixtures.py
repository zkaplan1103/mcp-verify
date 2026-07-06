"""Pydantic models the eval cases are written against.

Vendored from the grant-finder app so the frozen ground-truth cases port
unchanged: the field names and types here must stay byte-compatible with the
originals, because `eval.adapter.shared_prefix_text` renders these models as the
SOURCE text via a deterministic JSON dump. Only what the case files use is
vendored — no web/pipeline models.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FundingPreference(str, Enum):
    GRANT = "grant"
    LOAN = "loan"
    EITHER = "either"


class OrgBasics(BaseModel):
    """Required eligibility-gate fields."""

    is_501c3: bool = Field(..., description="Whether the org holds 501(c)(3) status.")
    annual_budget_usd: int = Field(..., ge=0, description="Annual operating budget in USD.")
    org_age_years: int = Field(..., ge=0, description="Years since the org was founded.")


class Geography(BaseModel):
    """Optional context. Blank is acceptable."""

    state: Optional[str] = Field(None, description="Two-letter US state code, e.g. 'CA'.")
    service_area: Optional[str] = Field(None, description="Free-text service area description.")
    disadvantaged_community: Optional[bool] = Field(
        None, description="Whether the org serves a designated disadvantaged community."
    )


class ProjectSpecifics(BaseModel):
    """Optional context. Blank is acceptable."""

    project_type: Optional[str] = Field(
        None, description="A more specific sub-type, e.g. 'rooftop solar', 'after-school program'."
    )
    size_kw: Optional[float] = Field(None, ge=0, description="System size in kW.")
    estimated_cost_usd: Optional[int] = Field(None, ge=0, description="Estimated project cost.")
    stage: Optional[str] = Field(None, description="e.g. 'planning', 'shovel-ready'.")
    amount_needed_usd: Optional[int] = Field(None, ge=0, description="Funding amount needed.")


class MissionPopulations(BaseModel):
    """Optional context. Blank is acceptable."""

    mission_statement: Optional[str] = Field(None, description="The org's mission statement.")
    populations_served: List[str] = Field(
        default_factory=list,
        description="e.g. ['low-income', 'tribal', 'rural'].",
    )


class Profile(BaseModel):
    """An applicant-org profile: required core + optional context."""

    org_basics: OrgBasics
    project_type: str = Field(
        ..., min_length=1,
        description="Funding focus, e.g. 'solar', 'youth literacy', 'food security'.",
    )
    funding_preference: FundingPreference

    geography: Geography = Field(default_factory=Geography)
    project: ProjectSpecifics = Field(default_factory=ProjectSpecifics)
    mission: MissionPopulations = Field(default_factory=MissionPopulations)


class OpportunitySource(str, Enum):
    GRANTS_GOV = "grants_gov"
    CURATED = "curated"


class Opportunity(BaseModel):
    id: str = Field(..., description="Stable id (grants.gov oppId, or curated slug).")
    source: OpportunitySource
    title: str
    agency: Optional[str] = None
    url: Optional[str] = None

    status: Optional[str] = None
    close_date: Optional[str] = None
    aln: Optional[str] = Field(None, description="Assistance Listing Number (CFDA).")
    typical_award: Optional[str] = Field(None, description="Curated typical award size.")

    eligibility_notes: Optional[str] = None
    description: Optional[str] = None


class DraftStatus(str, Enum):
    DRAFT = "draft"  # produced, not yet verified
    VERIFIED = "verified"  # passed the verify loop
    NEEDS_HUMAN = "needs_human"  # escalated with unresolved claims


class Draft(BaseModel):
    opportunity_id: str
    eligibility_summary: str
    boilerplate: str = Field(..., description="Org description, need statement, etc.")
    status: DraftStatus = DraftStatus.DRAFT
    revision: int = Field(0, ge=0, description="How many revise passes produced this draft.")
