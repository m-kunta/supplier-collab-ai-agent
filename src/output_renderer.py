"""Output rendering module.

Renders a completed :class:`~src.agent.BriefingContext` to the requested
output format (markdown or DOCX). Each renderer receives the full context
and is responsible for assembling the document structure from the pre-computed
engine outputs and the LLM-generated narrative.

Current status: scaffold stubs. Implemented in Phase 4.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Avoid circular import at runtime; BriefingContext is only needed for
    # type annotations in this module.
    from src.agent import BriefingContext

logger = logging.getLogger(__name__)


def render_markdown(ctx: BriefingContext) -> str:  # type: ignore[name-defined]
    """Render a completed briefing context to a markdown string.

    The output is a single markdown document structured as:

    1. Executive Summary (LLM-generated)
    2. Scorecard (computed by scorecard_engine, narrated by LLM)
    3. Benchmark Gaps (computed by benchmark_engine, if enabled)
    4. PO Risk Summary (computed by po_risk_engine)
    5. OOS Attribution (computed by oos_attribution, if data available)
    6. Promo Readiness (computed by promo_readiness, if data available)
    7. §7 Buyer Deep-Dive (expanded when persona_emphasis includes 'buyer')
    8. §8 Planner Deep-Dive (expanded when persona_emphasis includes 'planner')
    9. Recommended Talking Points (LLM-generated)

    Args:
        ctx: Fully populated :class:`~src.agent.BriefingContext`. All engine
            outputs and ``briefing_text`` must be set before calling this.

    Returns:
        A UTF-8 markdown string ready to write to ``output/<vendor>_<date>.md``.

    Raises:
        NotImplementedError: Until Phase 4 implementation.
    """
    raise NotImplementedError(
        "Markdown rendering is not yet implemented. "
        "See docs/implementation_plan.md Phase 4."
    )


def render_docx(ctx: BriefingContext, output_path: Path) -> Path:  # type: ignore[name-defined]
    """Render a completed briefing context to a ``.docx`` Word document.

    Uses the same section structure as :func:`render_markdown` with additional
    formatting: heading styles, a formatted scorecard table, a colour-coded PO
    risk table (red/yellow/green rows), and the Supplier Collab AI footer.

    Args:
        ctx: Fully populated :class:`~src.agent.BriefingContext`.
        output_path: Destination ``.docx`` file path. Parent directory must
            exist. Existing files are overwritten.

    Returns:
        The resolved ``output_path`` of the written document.

    Raises:
        NotImplementedError: Until Phase 4 implementation.
    """
    raise NotImplementedError(
        "DOCX rendering is not yet implemented. "
        "See docs/implementation_plan.md Phase 4."
    )


def write_output(
    ctx: BriefingContext,  # type: ignore[name-defined]
    output_dir: Path,
    output_format: str,
) -> dict[str, Any]:
    """Dispatch to the appropriate renderer(s) based on ``output_format``.

    Args:
        ctx: Fully populated :class:`~src.agent.BriefingContext`.
        output_dir: Directory to write output files into.
        output_format: One of ``'md'``, ``'docx'``, or ``'both'``.

    Returns:
        Dict with ``'md_path'`` and/or ``'docx_path'`` keys for each written file.

    Raises:
        ValueError: If ``output_format`` is not a recognised value.
        NotImplementedError: Until Phase 4 implementation.
    """
    if output_format not in {"md", "docx", "both"}:
        raise ValueError(
            f"Unknown output_format '{output_format}'. "
            "Expected one of: 'md', 'docx', 'both'."
        )
    raise NotImplementedError(
        "Output dispatch is not yet implemented. "
        "See docs/implementation_plan.md Phase 4."
    )
