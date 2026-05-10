from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BriefingCreate(BaseModel):
    """Request body aligned with ``cli.py`` / ``summarize_request()`` parameters."""

    vendor: str = Field(..., min_length=1, description="Vendor name or canonical vendor ID.")
    meeting_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Meeting date (YYYY-MM-DD).",
    )
    data_dir: str = Field(
        default="data/inbound/mock",
        description="Path to manifest-driven landing zone (relative to repo root or absolute).",
    )
    lookback_weeks: int = Field(default=13, ge=1, le=52)
    persona_emphasis: Literal["buyer", "planner", "both"] = "both"
    include_benchmarks: bool = True
    output_format: Literal["md", "docx", "both"] = "docx"
    category_filter: Optional[str] = None
    llm_provider: Optional[str] = Field(default=None, description="Override default LLM provider (anthropic/openai/google/groq).")
    llm_model: Optional[str] = Field(default=None, description="Override default LLM model string.")

class VendorCreate(BaseModel):
    """Payload for registering a new supplier during Production Onboarding."""
    vendor_id: str = Field(..., description="Unique alphanumeric ID for the vendor (e.g., 'VEN123').")
    vendor_name: str = Field(..., description="Full company name.")
    category: str = Field(..., description="Primary category or department.")
    tier: str = Field(..., description="Supplier tier (e.g., 'Tier 1', 'Tier 2').")

class VendorResponse(BaseModel):
    """Response returned when fetching or creating a vendor."""
    id: str
    vendor_id: str
    vendor_name: str
    category: str
    tier: str
    status: str
    created_at: str
