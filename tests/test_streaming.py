"""Phase 6 — streaming LLM tests.

Covers:
- ``generate_text_stream`` for Anthropic (text-delta yielding).
- ``generate_text_stream`` fallback for non-anthropic providers.
- ``summarize_request_stream`` emitting ``engines`` / ``token`` / ``done`` events.
- ``POST /api/briefings/stream`` SSE endpoint.
"""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.llm_providers import generate_text_stream


MOCK_DATA_DIR = Path("data/inbound/mock")


# ---------------------------------------------------------------------------
# generate_text_stream — Anthropic
# ---------------------------------------------------------------------------


class _FakeStream:
    """Minimal stand-in for anthropic's ``messages.stream()`` context manager."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @property
    def text_stream(self):
        return iter(self._chunks)


class TestGenerateTextStreamAnthropic(unittest.TestCase):
    @patch("src.llm_providers.anthropic")
    def test_yields_text_deltas(self, mock_ant):
        mock_ant.Anthropic.return_value.messages.stream.return_value = _FakeStream(
            ["Hello ", "world", "!"]
        )
        chunks = list(generate_text_stream("prompt", provider="anthropic"))
        self.assertEqual(chunks, ["Hello ", "world", "!"])
        self.assertEqual("".join(chunks), "Hello world!")

    @patch("src.llm_providers.anthropic")
    def test_skips_empty_chunks(self, mock_ant):
        mock_ant.Anthropic.return_value.messages.stream.return_value = _FakeStream(
            ["a", "", "b"]
        )
        chunks = list(generate_text_stream("prompt", provider="anthropic"))
        self.assertEqual(chunks, ["a", "b"])

    @patch("src.llm_providers.anthropic")
    def test_passes_params_to_stream_call(self, mock_ant):
        mock_ant.Anthropic.return_value.messages.stream.return_value = _FakeStream(["x"])
        list(
            generate_text_stream(
                "prompt",
                provider="anthropic",
                model="claude-3-5-sonnet-latest",
                temperature=0.4,
                max_tokens=1024,
            )
        )
        _, kwargs = mock_ant.Anthropic.return_value.messages.stream.call_args
        self.assertEqual(kwargs["model"], "claude-3-5-sonnet-latest")
        self.assertAlmostEqual(kwargs["temperature"], 0.4)
        self.assertEqual(kwargs["max_tokens"], 1024)


class TestGenerateTextStreamFallback(unittest.TestCase):
    def test_non_anthropic_falls_back_to_single_chunk(self):
        from src import llm_providers

        fake_caller = MagicMock(return_value="single-shot result")
        with patch.dict(
            llm_providers._PROVIDER_DISPATCH,
            {"openai": fake_caller},
        ):
            chunks = list(generate_text_stream("prompt", provider="openai"))
        self.assertEqual(chunks, ["single-shot result"])
        fake_caller.assert_called_once()


# ---------------------------------------------------------------------------
# summarize_request_stream
# ---------------------------------------------------------------------------


class TestSummarizeRequestStream(unittest.TestCase):
    def test_emits_engines_tokens_done(self):
        from src import agent as agent_mod

        # Patch the low-level streaming function at the import site used in agent.py.
        with patch.object(
            agent_mod,
            "generate_text_stream",
            return_value=iter(["Hello ", "briefing"]),
        ), patch.object(agent_mod, "write_output", return_value={"md_path": Path("output/mock.md")}):
            events = list(
                agent_mod.summarize_request_stream(
                    vendor="Northstar Foods Co",
                    meeting_date="2026-04-21",
                    data_dir=MOCK_DATA_DIR,
                    lookback_weeks=13,
                    persona_emphasis="both",
                    include_benchmarks=True,
                    output_format="md",
                    category_filter=None,
                )
            )

        types = [e["type"] for e in events]
        self.assertIn("engines", types)
        self.assertIn("token", types)
        self.assertEqual(types[-1], "done")

        engines_event = next(e for e in events if e["type"] == "engines")
        self.assertIn("scorecard", engines_event["engines"])
        self.assertIn("po_risk", engines_event["engines"])

        token_events = [e for e in events if e["type"] == "token"]
        joined = "".join(e["content"] for e in token_events)
        self.assertEqual(joined, "Hello briefing")

        done_event = events[-1]
        self.assertEqual(done_event["summary"]["status"], "complete")
        self.assertEqual(done_event["summary"]["briefing_text"], "Hello briefing")

    def test_emits_error_on_llm_failure(self):
        from src import agent as agent_mod

        def _boom(*_args, **_kwargs):
            raise RuntimeError("LLM exploded")
            yield  # pragma: no cover — unreachable

        with patch.object(agent_mod, "generate_text_stream", side_effect=_boom):
            events = list(
                agent_mod.summarize_request_stream(
                    vendor="Northstar Foods Co",
                    meeting_date="2026-04-21",
                    data_dir=MOCK_DATA_DIR,
                    lookback_weeks=13,
                    persona_emphasis="both",
                    include_benchmarks=True,
                    output_format="md",
                    category_filter=None,
                )
            )

        self.assertEqual(events[-1]["type"], "error")
        self.assertIn("LLM exploded", events[-1]["message"])


# ---------------------------------------------------------------------------
# POST /api/briefings/stream
# ---------------------------------------------------------------------------


def _parse_sse(body: str):
    """Parse an SSE stream body into a list of JSON payloads."""
    out = []
    for line in body.splitlines():
        if line.startswith("data: "):
            out.append(json.loads(line[len("data: "):]))
    return out


class TestStreamEndpoint(unittest.TestCase):
    def test_endpoint_streams_engines_tokens_done_and_persists(self):
        from api import main as api_main

        def _fake_stream(**_kwargs):
            yield {
                "type": "engines",
                "engines": {"scorecard": {"OTIF": {"current_value": 0.95}}},
            }
            yield {"type": "token", "content": "Hello "}
            yield {"type": "token", "content": "world"}
            yield {
                "type": "done",
                "summary": {
                    "status": "complete",
                    "briefing_text": "Hello world",
                    "request": {"vendor": "Acme Co"},
                },
            }

        with patch.object(api_main, "summarize_request_stream", _fake_stream):
            client = TestClient(api_main.app)
            resp = client.post(
                "/api/briefings/stream",
                json={"vendor": "Acme Co", "meeting_date": "2026-04-21"},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.headers["content-type"].startswith("text/event-stream"))
            events = _parse_sse(resp.text)

        types = [e["type"] for e in events]
        self.assertEqual(types, ["engines", "token", "token", "done"])

        done = events[-1]
        self.assertIn("id", done)
        self.assertIn("created_at", done)
        self.assertEqual(done["summary"]["briefing_text"], "Hello world")

        # Briefing persisted and retrievable via GET.
        get = client.get(f"/api/briefings/{done['id']}")
        self.assertEqual(get.status_code, 200)
        self.assertEqual(get.json()["briefing_text"], "Hello world")

    def test_endpoint_forwards_error_events(self):
        from api import main as api_main

        def _fake_stream(**_kwargs):
            yield {"type": "error", "message": "boom"}

        with patch.object(api_main, "summarize_request_stream", _fake_stream):
            client = TestClient(api_main.app)
            resp = client.post(
                "/api/briefings/stream",
                json={"vendor": "Acme Co", "meeting_date": "2026-04-21"},
            )
            events = _parse_sse(resp.text)

        self.assertEqual(events, [{"type": "error", "message": "boom"}])


if __name__ == "__main__":
    unittest.main()
