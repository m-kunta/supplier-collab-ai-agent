from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.benchmark_engine import compute_benchmarks
from src.asn_insights import compute_asn_insights
from src.chargeback_insights import compute_chargeback_insights
from src.config import load_config
from src.data_loader import load_dataset, load_manifest, load_vendor_data, resolve_vendor_id
from src.data_validator import (
    REQUIRED_FILES,
    ValidationResult,
    validate_dataset_frame,
    validate_manifest_shape,
)
from src.forecast_insights import compute_forecast_insights
from src.inventory_insights import compute_inventory_insights
from src.llm_providers import ProviderSelection, generate_text, generate_text_stream, resolve_provider
from src.oos_attribution import compute_oos_attribution
from src.output_renderer import write_output
from src.po_risk_engine import compute_po_risk
from src.prompt_builder import build_prompt
from src.promo_readiness import compute_promo_readiness
from src.scorecard_engine import compute_scorecard
from src.trade_fund_insights import compute_trade_fund_insights

logger = logging.getLogger(__name__)

class AgentPipelineError(Exception):
    """Exception raised when the pipeline fails, carrying context state."""
    def __init__(self, message: str, validation_report: dict[str, Any] | None = None):
        super().__init__(message)
        self.validation_report = validation_report


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
    validation_report: dict[str, Any] = field(default_factory=dict)
    provider_override: str | None = None
    model_override: str | None = None
    provider: ProviderSelection | None = None
    # vendor_data: dict[str, pd.DataFrame] — populated in Phase 3 data stage
    vendor_data: dict[str, Any] = field(default_factory=dict)

    # --- Phase 3 engine outputs (None = stage not yet run) ---
    scorecard: dict[str, Any] | None = None
    benchmarks: dict[str, Any] | None = None
    po_risk: dict[str, Any] | None = None
    oos_attribution: dict[str, Any] | None = None
    promo_readiness: dict[str, Any] | None = None
    inventory_insights: dict[str, Any] | None = None
    forecast_insights: dict[str, Any] | None = None
    asn_insights: dict[str, Any] | None = None
    chargeback_insights: dict[str, Any] | None = None
    trade_fund_insights: dict[str, Any] | None = None

    # --- Phase 4 output ---
    prompt: str = ""
    briefing_text: str | None = None
    output_files: dict[str, str] | None = None

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
    _ensure_validation_report(ctx)
    ctx.validation_result = validate_manifest_shape(ctx.manifest)
    ctx.validation_report["manifest"] = {
        "status": "failed" if ctx.validation_result.has_errors else "passed",
        "errors": list(ctx.validation_result.errors),
        "warnings": list(ctx.validation_result.warnings),
    }
    if ctx.validation_result.has_errors:
        _finalize_validation_report(ctx)
        raise ValueError(
            "Manifest validation failed — cannot proceed:\n"
            + "\n".join(f"  - {e}" for e in ctx.validation_result.errors)
        )
    for w in ctx.validation_result.warnings:
        logger.warning("Manifest validation warning: %s", w)
        ctx.add_note(f"Manifest warning: {w}")
    _finalize_validation_report(ctx)
    return ctx


def _stage_validate_datasets(ctx: BriefingContext) -> BriefingContext:
    _ensure_validation_report(ctx)
    if ctx.validation_result is None:
        ctx.validation_result = ValidationResult()

    fatal_errors: list[str] = []
    optional_datasets_to_skip: list[str] = []

    for dataset_name, metadata in list(ctx.manifest.get("files", {}).items()):
        is_required = dataset_name in REQUIRED_FILES or metadata.get("required", False)

        try:
            df = load_dataset(ctx.manifest, dataset_name)
        except FileNotFoundError as exc:
            message = f"{dataset_name}: {exc}"
            _record_dataset_validation(
                ctx,
                dataset_name,
                status="failed" if is_required else "warning",
                errors=[message] if is_required else [],
                warnings=[] if is_required else [message],
            )
            if is_required:
                fatal_errors.append(message)
            else:
                ctx.validation_result.warnings.append(message)
                optional_datasets_to_skip.append(dataset_name)
            continue

        try:
            dataset_result = validate_dataset_frame(dataset_name, df)
        except (FileNotFoundError, ValueError) as exc:
            message = f"{dataset_name}: {exc}"
            _record_dataset_validation(
                ctx,
                dataset_name,
                status="failed" if is_required else "warning",
                errors=[message] if is_required else [],
                warnings=[] if is_required else [message],
            )
            if is_required:
                fatal_errors.append(message)
            else:
                ctx.validation_result.warnings.append(message)
                optional_datasets_to_skip.append(dataset_name)
            continue

        if dataset_result.has_errors:
            prefixed = [f"{dataset_name}: {error}" for error in dataset_result.errors]
            _record_dataset_validation(
                ctx,
                dataset_name,
                status="failed" if is_required else "warning",
                errors=prefixed if is_required else [],
                warnings=[] if is_required else prefixed,
            )
            if is_required:
                fatal_errors.extend(prefixed)
            else:
                ctx.validation_result.warnings.extend(prefixed)
                optional_datasets_to_skip.append(dataset_name)
        else:
            _record_dataset_validation(
                ctx,
                dataset_name,
                status="passed",
                errors=[],
                warnings=[],
            )

    # Prune failed optional datasets from the manifest so downstream stages
    # (load_vendor_data etc.) don't attempt to load them.  ctx.manifest reflects
    # the effective set of usable files for this pipeline run, not the on-disk state.
    for dataset_name in optional_datasets_to_skip:
        ctx.manifest.get("files", {}).pop(dataset_name, None)
        ctx.add_note(
            f"Optional dataset '{dataset_name}' failed validation and will be skipped."
        )

    if fatal_errors:
        ctx.validation_result.errors.extend(fatal_errors)
        _finalize_validation_report(ctx)
        raise ValueError(
            "Dataset validation failed — cannot proceed:\n"
            + "\n".join(f"  - {error}" for error in fatal_errors)
        )

    for warning in ctx.validation_result.warnings:
        logger.warning("Dataset validation warning: %s", warning)

    _finalize_validation_report(ctx)
    return ctx


def _ensure_validation_report(ctx: BriefingContext) -> None:
    if ctx.validation_report:
        return
    ctx.validation_report = {
        "overall_status": "passed",
        "error_count": 0,
        "warning_count": 0,
        "manifest": {"status": "pending", "errors": [], "warnings": []},
        "datasets": {},
    }


def _record_dataset_validation(
    ctx: BriefingContext,
    dataset_name: str,
    *,
    status: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    _ensure_validation_report(ctx)
    ctx.validation_report.setdefault("datasets", {})[dataset_name] = {
        "status": status,
        "errors": list(errors),
        "warnings": list(warnings),
    }


def _finalize_validation_report(ctx: BriefingContext) -> None:
    _ensure_validation_report(ctx)
    manifest = ctx.validation_report.get("manifest", {})
    datasets = ctx.validation_report.get("datasets", {})

    error_count = len(manifest.get("errors", []))
    warning_count = len(manifest.get("warnings", []))

    for details in datasets.values():
        error_count += len(details.get("errors", []))
        warning_count += len(details.get("warnings", []))

    if error_count:
        overall_status = "failed"
    elif warning_count:
        overall_status = "warning"
    else:
        overall_status = "passed"

    ctx.validation_report["error_count"] = error_count
    ctx.validation_report["warning_count"] = warning_count
    ctx.validation_report["overall_status"] = overall_status


def _stage_resolve_provider(ctx: BriefingContext) -> BriefingContext:
    # Precedence: request override > LLM_PROVIDER env var > config default > "anthropic"
    override_provider = ctx.provider_override or os.getenv("LLM_PROVIDER")
    config_provider = ctx.config.get("llm", {}).get("default_provider")
    config_model = ctx.config.get("llm", {}).get("default_model")
    effective_provider = override_provider or config_provider

    # Only carry the config model when the provider hasn't changed; otherwise let
    # resolve_provider pick the default model for whichever provider was selected.
    provider_changed = override_provider and override_provider != config_provider
    effective_model = (
        ctx.model_override
        or os.getenv("LLM_MODEL")
        or (None if provider_changed else config_model)
    )
    ctx.provider = resolve_provider(effective_provider, effective_model)
    return ctx


def _stage_resolve_vendor_id(ctx: BriefingContext) -> BriefingContext:
    vendor_master_df = load_dataset(ctx.manifest, "vendor_master")
    ctx.vendor_id = resolve_vendor_id(
        ctx.vendor_input,
        vendor_master_df,
        category_filter=ctx.category_filter,
    )
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


def _meeting_date_as_date(meeting_date: str) -> date:
    return datetime.strptime(meeting_date.strip(), "%Y-%m-%d").date()


def _stage_compute_scorecard(ctx: BriefingContext) -> BriefingContext:
    perf = ctx.vendor_data.get("vendor_performance")
    if perf is None:
        ctx.add_note("Scorecard skipped: vendor_performance not loaded.")
        ctx.scorecard = None
        return ctx
    ctx.scorecard = compute_scorecard(
        ctx.vendor_id,
        perf,
        ctx.lookback_weeks,
        ctx.config,
    )
    return ctx


def _stage_compute_benchmarks(ctx: BriefingContext) -> BriefingContext:
    if not ctx.include_benchmarks:
        ctx.add_note("Benchmarks skipped: include_benchmarks is false.")
        ctx.benchmarks = None
        return ctx
    try:
        perf_all = load_dataset(ctx.manifest, "vendor_performance")
    except (KeyError, FileNotFoundError) as exc:
        ctx.add_note(f"Benchmarks skipped: cannot load vendor_performance ({exc}).")
        ctx.benchmarks = None
        return ctx
    ctx.benchmarks = compute_benchmarks(ctx.vendor_id, perf_all, ctx.config)
    if not ctx.benchmarks:
        ctx.add_note("Benchmarks returned empty (insufficient peer or metric data).")
    return ctx


def _stage_compute_po_risk(ctx: BriefingContext) -> BriefingContext:
    po = ctx.vendor_data.get("purchase_orders")
    if po is None:
        ctx.add_note("PO risk skipped: purchase_orders not loaded.")
        ctx.po_risk = None
        return ctx
    ref = _meeting_date_as_date(ctx.meeting_date)
    ctx.po_risk = compute_po_risk(ctx.vendor_id, po, ctx.config, reference_date=ref)
    return ctx


def _stage_compute_oos_attribution(ctx: BriefingContext) -> BriefingContext:
    if "oos_events" not in ctx.vendor_data:
        ctx.add_note("OOS attribution skipped: oos_events not in landing zone.")
        ctx.oos_attribution = None
        return ctx
    oos_df = ctx.vendor_data["oos_events"]
    po_df = ctx.vendor_data.get("purchase_orders", pd.DataFrame())
    ref = _meeting_date_as_date(ctx.meeting_date)
    ctx.oos_attribution = compute_oos_attribution(
        ctx.vendor_id,
        oos_df,
        po_df,
        ctx.config,
        reference_date=ref,
    )
    return ctx


def _stage_compute_promo_readiness(ctx: BriefingContext) -> BriefingContext:
    if "promo_calendar" not in ctx.vendor_data:
        ctx.add_note("Promo readiness skipped: promo_calendar not in landing zone.")
        ctx.promo_readiness = None
        return ctx
    promo_df = ctx.vendor_data["promo_calendar"]
    po_df = ctx.vendor_data.get("purchase_orders", pd.DataFrame())
    ctx.promo_readiness = compute_promo_readiness(
        ctx.vendor_id,
        promo_df,
        po_df,
        ctx.config,
    )
    return ctx


def _stage_compute_inventory_insights(ctx: BriefingContext) -> BriefingContext:
    if "inventory_position" not in ctx.vendor_data:
        ctx.add_note("Inventory insights skipped: inventory_position not in landing zone.")
        ctx.inventory_insights = None
        return ctx
    inventory_df = ctx.vendor_data["inventory_position"]
    promo_df = ctx.vendor_data.get("promo_calendar", pd.DataFrame())
    ref = _meeting_date_as_date(ctx.meeting_date)
    ctx.inventory_insights = compute_inventory_insights(
        ctx.vendor_id,
        inventory_df,
        promo_df,
        reference_date=ref,
    )
    return ctx


def _stage_compute_forecast_insights(ctx: BriefingContext) -> BriefingContext:
    if "demand_forecast" not in ctx.vendor_data:
        ctx.add_note("Forecast insights skipped: demand_forecast not in landing zone.")
        ctx.forecast_insights = None
        return ctx
    forecast_df = ctx.vendor_data["demand_forecast"]
    ref = _meeting_date_as_date(ctx.meeting_date)
    ctx.forecast_insights = compute_forecast_insights(
        ctx.vendor_id,
        forecast_df,
        reference_date=ref,
    )
    return ctx


def _stage_compute_asn_insights(ctx: BriefingContext) -> BriefingContext:
    if "asn_receipts" not in ctx.vendor_data:
        ctx.add_note("ASN insights skipped: asn_receipts not in landing zone.")
        ctx.asn_insights = None
        return ctx
    ref = _meeting_date_as_date(ctx.meeting_date)
    ctx.asn_insights = compute_asn_insights(
        ctx.vendor_id,
        ctx.vendor_data["asn_receipts"],
        reference_date=ref,
    )
    return ctx


def _stage_compute_chargeback_insights(ctx: BriefingContext) -> BriefingContext:
    if "chargebacks" not in ctx.vendor_data:
        ctx.add_note("Chargeback insights skipped: chargebacks not in landing zone.")
        ctx.chargeback_insights = None
        return ctx
    ref = _meeting_date_as_date(ctx.meeting_date)
    ctx.chargeback_insights = compute_chargeback_insights(
        ctx.vendor_id,
        ctx.vendor_data["chargebacks"],
        reference_date=ref,
    )
    return ctx


def _stage_compute_trade_fund_insights(ctx: BriefingContext) -> BriefingContext:
    if "trade_funds" not in ctx.vendor_data:
        ctx.add_note("Trade fund insights skipped: trade_funds not in landing zone.")
        ctx.trade_fund_insights = None
        return ctx
    ref = _meeting_date_as_date(ctx.meeting_date)
    promo_df = ctx.vendor_data.get("promo_calendar", pd.DataFrame())
    ctx.trade_fund_insights = compute_trade_fund_insights(
        ctx.vendor_id,
        ctx.vendor_data["trade_funds"],
        promo_df,
        reference_date=ref,
    )
    return ctx


def _stage_assemble_prompt(ctx: BriefingContext) -> BriefingContext:
    """Build the full LLM prompt from engine outputs and the prompt template."""
    ctx.prompt = build_prompt(ctx)
    ctx.add_note(f"Prompt assembled ({len(ctx.prompt)} chars).")
    return ctx


def _stage_generate_briefing(ctx: BriefingContext) -> BriefingContext:
    """Call the configured LLM provider and store the generated briefing text."""
    llm_cfg = ctx.config.get("llm", {})
    ctx.briefing_text = generate_text(
        ctx.prompt,
        provider=ctx.provider.provider if ctx.provider else None,
        model=ctx.provider.model if ctx.provider else None,
        temperature=llm_cfg.get("temperature"),
        max_tokens=llm_cfg.get("max_tokens"),
        max_retries=llm_cfg.get("retry_count", 3),
    )
    ctx.add_note(
        f"Briefing generated ({len(ctx.briefing_text)} chars "
        f"via {ctx.provider.provider if ctx.provider else 'unknown'})."
    )
    return ctx


def _stage_render_output(ctx: BriefingContext) -> BriefingContext:
    """Render and write the briefing document to the output directory."""
    output_dir_str = ctx.config.get("output", {}).get("output_dir", "output/")
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = write_output(ctx, output_dir=output_dir, output_format=ctx.output_format)
    ctx.output_files = {k: str(v) for k, v in result.items() if v}
    paths = ", ".join(str(v) for v in result.values() if v)
    ctx.add_note(f"Output written: {paths}")
    return ctx


def run_pipeline(ctx: BriefingContext) -> BriefingContext:
    """Execute the briefing pipeline in stage order.

    Stages are run sequentially. Each stage is responsible for populating
    its slice of the context. Future phases add stages here without
    changing the function signature or the caller.

    Stages:
      1.  Load config
      2.  Load manifest
      3.  Validate manifest (fatal gate)
      4.  Resolve LLM provider
      5.  Resolve vendor ID (name → canonical ID)
      6.  Load vendor-scoped DataFrames
      7.  Compute scorecard
      8.  Compute benchmarks (if ``include_benchmarks``; uses full vendor_performance)
      9.  Compute PO risk
      10. Compute OOS attribution (if ``oos_events`` loaded)
      11. Compute promo readiness (if ``promo_calendar`` loaded)
      12. Assemble prompt (prompt_builder)
      13. Generate briefing text via LLM
      14. Render and write output file(s)
    """
    logger.info(
        "Pipeline starting: vendor='%s', date='%s', data_dir='%s'",
        ctx.vendor_input, ctx.meeting_date, ctx.data_dir,
    )
    ctx = _stage_load_config(ctx)
    ctx = _stage_load_manifest(ctx)
    ctx = _stage_validate_manifest(ctx)
    ctx = _stage_validate_datasets(ctx)
    ctx = _stage_resolve_provider(ctx)
    ctx = _stage_resolve_vendor_id(ctx)
    ctx = _stage_load_vendor_data(ctx)

    ctx = _stage_compute_scorecard(ctx)
    ctx = _stage_compute_benchmarks(ctx)
    ctx = _stage_compute_po_risk(ctx)
    ctx = _stage_compute_oos_attribution(ctx)
    ctx = _stage_compute_promo_readiness(ctx)
    ctx = _stage_compute_inventory_insights(ctx)
    ctx = _stage_compute_forecast_insights(ctx)
    ctx = _stage_compute_asn_insights(ctx)
    ctx = _stage_compute_chargeback_insights(ctx)
    ctx = _stage_compute_trade_fund_insights(ctx)

    ctx = _stage_assemble_prompt(ctx)
    ctx = _stage_generate_briefing(ctx)
    ctx = _stage_render_output(ctx)

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
    llm_provider: str | None = None,
    llm_model: str | None = None,
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
        provider_override=llm_provider,
        model_override=llm_model,
    )
    try:
        ctx = run_pipeline(ctx)
    except Exception as exc:
        raise AgentPipelineError(str(exc), getattr(ctx, "validation_report", None)) from exc

    status = "complete" if ctx.briefing_text else "partial"
    return {
        "status": status,
        "message": (
            "Briefing generated successfully."
            if ctx.briefing_text
            else "Compute engines complete; LLM briefing not generated."
        ),
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
        "validation_report": ctx.validation_report,
        "pipeline_notes": ctx.pipeline_notes,
        "scorecard": ctx.scorecard,
        "benchmarks": ctx.benchmarks,
        "po_risk": ctx.po_risk,
        "oos_attribution": ctx.oos_attribution,
        "promo_readiness": ctx.promo_readiness,
        "inventory_insights": ctx.inventory_insights,
        "forecast_insights": ctx.forecast_insights,
        "asn_insights": ctx.asn_insights,
        "chargeback_insights": ctx.chargeback_insights,
        "trade_fund_insights": ctx.trade_fund_insights,
        "briefing_text": ctx.briefing_text,
        "output_files": ctx.output_files,
    }


# ---------------------------------------------------------------------------
# Phase 6 — Streaming orchestrator
# ---------------------------------------------------------------------------


def _serialize_ctx_summary(ctx: BriefingContext) -> dict[str, Any]:
    """Serialize a completed context the same way ``summarize_request`` does."""
    status = "complete" if ctx.briefing_text else "partial"
    return {
        "status": status,
        "message": (
            "Briefing generated successfully."
            if ctx.briefing_text
            else "Compute engines complete; LLM briefing not generated."
        ),
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
        "validation_report": ctx.validation_report,
        "pipeline_notes": ctx.pipeline_notes,
        "scorecard": ctx.scorecard,
        "benchmarks": ctx.benchmarks,
        "po_risk": ctx.po_risk,
        "oos_attribution": ctx.oos_attribution,
        "promo_readiness": ctx.promo_readiness,
        "inventory_insights": ctx.inventory_insights,
        "forecast_insights": ctx.forecast_insights,
        "asn_insights": ctx.asn_insights,
        "chargeback_insights": ctx.chargeback_insights,
        "trade_fund_insights": ctx.trade_fund_insights,
        "briefing_text": ctx.briefing_text,
        "output_files": ctx.output_files,
    }


def summarize_request_stream(
    *,
    vendor: str,
    meeting_date: str,
    data_dir: Path,
    lookback_weeks: int,
    persona_emphasis: str,
    include_benchmarks: bool,
    output_format: str,
    category_filter: str | None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
):
    """Stream the briefing pipeline stage-by-stage.

    This is the Phase 6 streaming counterpart to :func:`summarize_request`.  It
    runs the deterministic compute engines synchronously, then streams LLM
    tokens as they arrive from the provider, and finally persists the briefing
    to disk.

    Yields dict events for the caller (typically a FastAPI SSE endpoint) to
    forward to the browser:

    - ``{"type": "engines", "engines": {...}}`` — emitted once after compute
      engines finish, carrying the full engine payload so the UI can paint
      dashboards immediately.
    - ``{"type": "token", "content": "..."}`` — one per LLM text delta.
    - ``{"type": "done", "summary": {...}}`` — final event with the full
      CLI-shaped summary dict (same shape as :func:`summarize_request`).
    - ``{"type": "error", "message": "..."}`` — emitted on failure; the
      caller should then stop the stream.
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
        provider_override=llm_provider,
        model_override=llm_model,
    )

    try:
        ctx = _stage_load_config(ctx)
        ctx = _stage_load_manifest(ctx)
        ctx = _stage_validate_manifest(ctx)
        ctx = _stage_validate_datasets(ctx)
        ctx = _stage_resolve_provider(ctx)
        ctx = _stage_resolve_vendor_id(ctx)
        ctx = _stage_load_vendor_data(ctx)

        ctx = _stage_compute_scorecard(ctx)
        ctx = _stage_compute_benchmarks(ctx)
        ctx = _stage_compute_po_risk(ctx)
        ctx = _stage_compute_oos_attribution(ctx)
        ctx = _stage_compute_promo_readiness(ctx)
        ctx = _stage_compute_inventory_insights(ctx)
        ctx = _stage_compute_forecast_insights(ctx)
        ctx = _stage_compute_asn_insights(ctx)
        ctx = _stage_compute_chargeback_insights(ctx)
        ctx = _stage_compute_trade_fund_insights(ctx)

        ctx = _stage_assemble_prompt(ctx)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stream pipeline failed before LLM call.")
        yield {
            "type": "error",
            "message": str(exc),
            "validation_report": getattr(ctx, "validation_report", None)
        }
        return

    # Emit engine payload up-front so the UI can render dashboards immediately.
    yield {
        "type": "engines",
        "engines": {
            "vendor_id": ctx.vendor_id,
            "scorecard": ctx.scorecard,
            "benchmarks": ctx.benchmarks,
            "po_risk": ctx.po_risk,
            "oos_attribution": ctx.oos_attribution,
            "promo_readiness": ctx.promo_readiness,
            "inventory_insights": ctx.inventory_insights,
            "forecast_insights": ctx.forecast_insights,
            "asn_insights": ctx.asn_insights,
            "chargeback_insights": ctx.chargeback_insights,
            "trade_fund_insights": ctx.trade_fund_insights,
            "llm_selection": {
                "provider": ctx.provider.provider if ctx.provider else None,
                "model": ctx.provider.model if ctx.provider else None,
            },
        },
    }

    # Stream tokens from the LLM, accumulating into ctx.briefing_text.
    llm_cfg = ctx.config.get("llm", {})
    collected: list[str] = []
    try:
        for chunk in generate_text_stream(
            ctx.prompt,
            provider=ctx.provider.provider if ctx.provider else None,
            model=ctx.provider.model if ctx.provider else None,
            temperature=llm_cfg.get("temperature"),
            max_tokens=llm_cfg.get("max_tokens"),
        ):
            if not chunk:
                continue
            collected.append(chunk)
            yield {"type": "token", "content": chunk}
    except Exception as exc:  # noqa: BLE001
        logger.exception("LLM streaming failed.")
        yield {"type": "error", "message": str(exc)}
        return

    ctx.briefing_text = "".join(collected)
    ctx.add_note(
        f"Briefing streamed ({len(ctx.briefing_text)} chars "
        f"via {ctx.provider.provider if ctx.provider else 'unknown'})."
    )

    # Persist to disk using the same renderer as the sync path.
    try:
        ctx = _stage_render_output(ctx)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Render/output stage failed after streaming.")
        yield {"type": "error", "message": str(exc)}
        return

    yield {"type": "done", "summary": _serialize_ctx_summary(ctx)}
