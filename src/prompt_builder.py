"""Prompt assembly module for the Supplier Collab AI Agent.

Responsibilities:
  - Load the versioned prompt template from ``prompts/``.
  - Serialise :class:`~src.agent.BriefingContext` engine outputs into a
    structured JSON payload.
  - Substitute template variables and return a ready-to-send prompt string.

Design intent:
  Claude narrates pre-computed data; it does not recompute numbers.
  All analytical work is done deterministically in the engine layer before
  this module is called (scope doc §14).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.agent import BriefingContext

logger = logging.getLogger(__name__)

# Root of the project (two levels up from this file: src/ → project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default prompt template version for Phase 4
_DEFAULT_PROMPT_VERSION = "briefing_v1"


def _load_template(version: str = _DEFAULT_PROMPT_VERSION) -> str:
    """Load a prompt template from ``prompts/``.

    Args:
        version: Filename stem under ``prompts/`` (without ``.md``).

    Returns:
        The raw template string.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    template_path = _PROJECT_ROOT / "prompts" / f"{version}.md"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Prompt template not found: {template_path}. "
            "Ensure the prompts/ directory and the requested version file exist."
        )
    text = template_path.read_text(encoding="utf-8")
    logger.debug("Loaded prompt template '%s' (%d chars).", version, len(text))
    return text


def _serialise_engine_outputs(ctx: BriefingContext) -> dict[str, Any]:  # type: ignore[name-defined]
    """Collect all engine outputs from *ctx* into a JSON-serialisable dict.

    Keys present reflect which engines ran successfully.  Missing optional
    data (OOS, promo) is represented as ``null`` rather than being omitted so
    the LLM prompt template can produce graceful-degradation messages.

    Args:
        ctx: A :class:`~src.agent.BriefingContext` after all compute stages
            have been executed.

    Returns:
        A dict ready to be serialised to JSON and injected into the prompt.
    """
    return {
        "vendor_id": ctx.vendor_id,
        "meeting_date": ctx.meeting_date,
        "persona_emphasis": ctx.persona_emphasis,
        "lookback_weeks": ctx.lookback_weeks,
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
        "pipeline_notes": ctx.pipeline_notes,
    }


def build_prompt(
    ctx: BriefingContext,  # type: ignore[name-defined]
    *,
    template_version: str = _DEFAULT_PROMPT_VERSION,
    indent: int = 2,
) -> str:
    """Assemble the full LLM prompt for a given briefing context.

    Loads ``prompts/{template_version}.md``, serialises engine outputs to a
    JSON payload, and performs template variable substitution.

    Template variables substituted:
      - ``{{DATA_PAYLOAD}}``     — JSON-encoded engine outputs.
      - ``{{PERSONA_EMPHASIS}}`` — value of ``ctx.persona_emphasis``.
      - ``{{VENDOR_ID}}``        — resolved vendor ID.
      - ``{{MEETING_DATE}}``     — meeting date string.

    Args:
        ctx: Fully populated :class:`~src.agent.BriefingContext` after all
            compute stages have run.
        template_version: Prompt template filename stem to use.
            Defaults to ``'briefing_v1'``.
        indent: JSON indentation level for the data payload.

    Returns:
        The complete prompt string ready to pass to ``generate_text()``.
    """
    template = _load_template(template_version)
    payload = _serialise_engine_outputs(ctx)
    payload_json = json.dumps(payload, indent=indent, default=str)

    prompt = template.replace("{{DATA_PAYLOAD}}", payload_json)
    prompt = prompt.replace("{{PERSONA_EMPHASIS}}", ctx.persona_emphasis)
    prompt = prompt.replace("{{VENDOR_ID}}", ctx.vendor_id)
    prompt = prompt.replace("{{MEETING_DATE}}", ctx.meeting_date)

    logger.info(
        "Assembled prompt: template='%s', payload_keys=%s, total_chars=%d.",
        template_version,
        sorted(payload.keys()),
        len(prompt),
    )
    return prompt
