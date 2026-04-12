"""Tests for src/prompt_builder.py — prompt assembly.

No API calls are made; tests verify template loading, variable substitution,
and graceful handling of missing optional engine outputs.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_ctx(
    *,
    vendor_id: str = "KELLOGGS",
    meeting_date: str = "2026-04-03",
    persona_emphasis: str = "both",
    lookback_weeks: int = 13,
    scorecard: dict | None = None,
    benchmarks: dict | None = None,
    po_risk: dict | None = None,
    oos_attribution: dict | None = None,
    promo_readiness: dict | None = None,
    pipeline_notes: list | None = None,
):
    """Return a minimal mock BriefingContext with the given engine outputs."""
    ctx = MagicMock()
    ctx.vendor_id = vendor_id
    ctx.meeting_date = meeting_date
    ctx.persona_emphasis = persona_emphasis
    ctx.lookback_weeks = lookback_weeks
    ctx.scorecard = scorecard or {"FILL_RATE": {"current_value": 0.94}}
    ctx.benchmarks = benchmarks
    ctx.po_risk = po_risk
    ctx.oos_attribution = oos_attribution
    ctx.promo_readiness = promo_readiness
    ctx.pipeline_notes = pipeline_notes or []
    return ctx


class TestBuildPromptTemplateLoading(unittest.TestCase):
    """Template loading and FileNotFoundError on missing version."""

    def test_raises_if_template_missing(self):
        from src.prompt_builder import build_prompt

        ctx = _make_ctx()
        with self.assertRaises(FileNotFoundError):
            build_prompt(ctx, template_version="briefing_v99_does_not_exist")

    def test_loads_briefing_v1_successfully(self):
        from src.prompt_builder import build_prompt

        ctx = _make_ctx()
        result = build_prompt(ctx)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 100)


class TestBuildPromptVariableSubstitution(unittest.TestCase):
    """Template variables are substituted correctly."""

    def setUp(self):
        from src.prompt_builder import build_prompt
        self.build_prompt = build_prompt
        self.ctx = _make_ctx(
            vendor_id="ACME_CORP",
            meeting_date="2026-05-01",
            persona_emphasis="buyer",
        )

    def test_vendor_id_substituted(self):
        result = self.build_prompt(self.ctx)
        self.assertIn("ACME_CORP", result)

    def test_meeting_date_substituted(self):
        result = self.build_prompt(self.ctx)
        self.assertIn("2026-05-01", result)

    def test_persona_emphasis_substituted(self):
        result = self.build_prompt(self.ctx)
        self.assertIn("buyer", result)

    def test_no_unresolved_placeholders(self):
        result = self.build_prompt(self.ctx)
        self.assertNotIn("{{DATA_PAYLOAD}}", result)
        self.assertNotIn("{{PERSONA_EMPHASIS}}", result)
        self.assertNotIn("{{VENDOR_ID}}", result)
        self.assertNotIn("{{MEETING_DATE}}", result)


class TestBuildPromptDataPayload(unittest.TestCase):
    """Engine output serialisation into the data payload."""

    def test_scorecard_present_in_payload(self):
        from src.prompt_builder import build_prompt

        scorecard = {"FILL_RATE": {"current_value": 0.94, "trend_direction": "improving"}}
        ctx = _make_ctx(scorecard=scorecard)
        result = build_prompt(ctx)
        self.assertIn("FILL_RATE", result)
        self.assertIn("0.94", result)

    def test_null_optional_outputs_present_as_null(self):
        """Missing optional data must appear as JSON null, not be omitted."""
        from src.prompt_builder import build_prompt

        ctx = _make_ctx(oos_attribution=None, promo_readiness=None)
        result = build_prompt(ctx)
        # The JSON payload should contain null keys, not be absent
        self.assertIn('"oos_attribution": null', result)
        self.assertIn('"promo_readiness": null', result)

    def test_payload_is_valid_json_when_extracted(self):
        from src.prompt_builder import build_prompt

        ctx = _make_ctx()
        result = build_prompt(ctx)
        # Extract content between <data_payload> tags
        start = result.index("<data_payload>") + len("<data_payload>")
        end = result.index("</data_payload>")
        payload_str = result[start:end].strip()
        # Must be valid JSON
        payload = json.loads(payload_str)
        self.assertIn("vendor_id", payload)
        self.assertIn("scorecard", payload)

    def test_pipeline_notes_included(self):
        from src.prompt_builder import build_prompt

        ctx = _make_ctx(pipeline_notes=["OOS data skipped", "Promo data loaded"])
        result = build_prompt(ctx)
        self.assertIn("OOS data skipped", result)


class TestBuildPromptPersonaVariants(unittest.TestCase):
    """Persona emphasis value appears correctly for all variants."""

    def _build(self, persona):
        from src.prompt_builder import build_prompt
        ctx = _make_ctx(persona_emphasis=persona)
        return build_prompt(ctx)

    def test_buyer_persona(self):
        result = self._build("buyer")
        self.assertIn("buyer", result)

    def test_planner_persona(self):
        result = self._build("planner")
        self.assertIn("planner", result)

    def test_both_persona(self):
        result = self._build("both")
        self.assertIn("both", result)


if __name__ == "__main__":
    unittest.main()
