from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import load_config
from src.data_loader import load_dataset, load_manifest, load_vendor_data, resolve_vendor_id
from src.data_validator import ValidationResult, validate_manifest_shape
from src.llm_providers import ProviderSelection, resolve_provider

logger = logging.getLogger(__name__)


@dataclass
class BriefingContext:
    """Accumulates state as the briefing pipeline progresses through stages.

    Each pipeline stage receives the context, populates its output fields,
    and returns it. Stages that are not yet implemented leave their output
    fields as ``None`` and append a note to ``pipeline_notes``.

    Design intent:
    - Inputs are set once at construction and never mutated.
    - Resolved state (config, manifest, vendor_id, etc.) is populated by
      dedicated ``_stage_*`` functions in order.
    - Engine outputs (scorecard, benchmarks, etc.) are populated in Phase 3.
    - ``pipeline_notes`` accumulates degradation notes and skip reasons so
      the final briefing can explain gaps transparently.
    """

    # --- Inputs (required at construction) ---
    vendor_input: str
    meeting_date: str
    data_dir: Path
    lookback_weeks: int
    persona_emphasis: str
    include_benchmarks: bool
    output_format: str
    category_filter: str | None

    # --- Resolved during pipeline (populated by stages) ---
    config: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)
    vendor_id: str = ""
    validation_result: ValidationResult | None = None
    provider: ProviderSelection | None = None
    # vendor_data: dict[str, pd.DataFrame] — populated in Phase 3 data stage
    vendor_data: dict[str, Any] = field(default_factory=dict)

    # --- Phase 3 engine outputs (None = stage not yet run) ---
    scorecard: dict[str, Any] | None = None
    benchmarks: dict[str, Any] | None = None
    po_risk: dict[str, Any] | None = None
    oos_attribution: dict[str, Any] | None = None
    promo_readiness: dict[str, Any] | None = None

    # --- Phase 4 output ---
    briefing_text: str | None = None

    # --- Pipeline metadata ---
    pipeline_notes: list[str] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        """Append a degradation note or pipeline annotation."""
        logger.info("Pipeline note: %s", note)
        self.pipeline_notes.append(note)


# ---------------------------------------------------------------------------
# Pipeline stages — each accepts and returns a BriefingContext.
# Stages are intentionally thin; orchestration logic lives in run_pipeline().
# ---------------------------------------------------------------------------

def _stage_load_config(ctx: BriefingContext) -> BriefingContext:
    ctx.config = load_config()
    return ctx


def _stage_load_manifest(ctx: BriefingContext) -> BriefingContext:
    ctx.manifest = load_manifest(ctx.data_dir)
    return ctx


def _stage_validate_manifest(ctx: BriefingContext) -> BriefingContext:
    ctx.validation_result = validate_manifest_shape(ctx.manifest)
    if ctx.validation_result.has_errors:
        raise ValueError(
            "Manifest validation failed — cannot proceed:\n"
            + "\n".join(f"  - {e}" for e in ctx.validation_result.errors)
        )
    for w in ctx.validation_result.warnings:
        logger.warning("Manifest validation warning: %s", w)
        ctx.add_note(f"Manifest warning: {w}")
    return ctx


def _stage_resolve_provider(ctx: BriefingContext) -> BriefingContext:
    ctx.provider = resolve_provider(
        ctx.config.get("llm", {}).get("default_provider"),
        ctx.config.get("llm", {}).get("default_model"),
    )
    return ctx


def _stage_resolve_vendor_id(ctx: BriefingContext) -> BriefingContext:
    vendor_master_df = load_dataset(ctx.manifest, "vendor_master")
    ctx.vendor_id = resolve_vendor_id(ctx.vendor_input, vendor_master_df)
    logger.info(
        "Resolved vendor input '%s' to vendor_id '%s'.",
        ctx.vendor_input,
        ctx.vendor_id,
    )
    return ctx


def _stage_load_vendor_data(ctx: BriefingContext) -> BriefingContext:
    if not ctx.vendor_id:
        raise ValueError("Vendor ID must be resolved before loading vendor data.")
    ctx.vendor_data = load_vendor_data(ctx.manifest, ctx.vendor_id)
    ctx.add_note(
        f"Loaded {len(ctx.vendor_data)} dataset(s) for vendor_id '{ctx.vendor_id}'."
    )
    return ctx


def run_pipeline(ctx: BriefingContext) -> BriefingContext:
    """Execute the briefing pipeline in stage order.

    Stages are run sequentially. Each stage is responsible for populating
    its slice of the context. Future phases add stages here without
    changing the function signature or the caller.

    Current stages (scaffold):
      1. Load config
      2. Load manifest
      3. Validate manifest (fatal gate)
      4. Resolve LLM provider
      5. Resolve vendor ID (name → canonical ID)
      6. Load vendor-scoped DataFrames

    Phase 3 will add:
      7. Compute scorecard
      8. Compute benchmarks (if enabled)
      9. Compute PO risk
      10. Compute OOS attribution (if data available)
      11. Compute promo readiness (if data available)

    Phase 4 will add:
      12. Assemble prompt
      13. Generate briefing text via LLM
      14. Render to output format
    """
    logger.info(
        "Pipeline starting: vendor='%s', date='%s', data_dir='%s'",
        ctx.vendor_input, ctx.meeting_date, ctx.data_dir,
    )
    ctx = _stage_load_config(ctx)
    ctx = _stage_load_manifest(ctx)
    ctx = _stage_validate_manifest(ctx)
    ctx = _stage_resolve_provider(ctx)
    ctx = _stage_resolve_vendor_id(ctx)
    ctx = _stage_load_vendor_data(ctx)

    ctx.add_note("Scaffold: briefing generation not yet implemented (Phase 4).")
    logger.info("Pipeline complete. Notes: %d", len(ctx.pipeline_notes))
    return ctx


# ---------------------------------------------------------------------------
# Public entry point — kept as the stable external API
# ---------------------------------------------------------------------------

def summarize_request(
    *,
    vendor: str,
    meeting_date: str,
    data_dir: Path,
    lookback_weeks: int,
    persona_emphasis: str,
    include_benchmarks: bool,
    output_format: str,
    category_filter: str | None,
) -> dict[str, Any]:
    """Run the briefing pipeline and return a scaffold summary dict.

    This is the stable CLI-facing entry point. Internally it builds a
    :class:`BriefingContext`, runs :func:`run_pipeline`, and serialises
    the result to a dict. As phases are implemented the dict will grow
    to include computed sections before eventually being replaced by
    a rendered briefing document.
    """
    ctx = BriefingContext(
        vendor_input=vendor,
        meeting_date=meeting_date,
        data_dir=data_dir,
        lookback_weeks=lookback_weeks,
        persona_emphasis=persona_emphasis,
        include_benchmarks=include_benchmarks,
        output_format=output_format,
        category_filter=category_filter,
    )
    ctx = run_pipeline(ctx)

    return {
        "status": "scaffold",
        "message": "Briefing generation is not implemented yet.",
        "request": {
            "vendor": ctx.vendor_input,
            "meeting_date": ctx.meeting_date,
            "data_dir": str(ctx.data_dir),
            "lookback_weeks": ctx.lookback_weeks,
            "persona_emphasis": ctx.persona_emphasis,
            "include_benchmarks": ctx.include_benchmarks,
            "output_format": ctx.output_format,
            "category_filter": ctx.category_filter,
        },
        "config_defaults": ctx.config.get("defaults", {}),
        "llm_selection": {
            "provider": ctx.provider.provider if ctx.provider else None,
            "model": ctx.provider.model if ctx.provider else None,
        },
        "vendor_id": ctx.vendor_id,
        "manifest_path": ctx.manifest.get("_manifest_path"),
        "available_file_keys": sorted(ctx.manifest.get("files", {}).keys()),
        "loaded_datasets": sorted(ctx.vendor_data.keys()),
        "validation_warnings": ctx.validation_result.warnings if ctx.validation_result else [],
        "pipeline_notes": ctx.pipeline_notes,
    }
