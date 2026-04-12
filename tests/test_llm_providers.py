"""Tests for src/llm_providers.py — all four provider implementations.

All SDK calls are mocked so no API keys are required.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.llm_providers import (
    DEFAULT_MODELS,
    _DEFAULT_MAX_TOKENS,
    _DEFAULT_TEMPERATURE,
    generate_text,
    resolve_provider,
)


# ---------------------------------------------------------------------------
# resolve_provider
# ---------------------------------------------------------------------------

class TestResolveProvider(unittest.TestCase):
    def test_defaults_to_anthropic(self):
        sel = resolve_provider()
        self.assertEqual(sel.provider, "anthropic")
        self.assertEqual(sel.model, DEFAULT_MODELS["anthropic"])

    def test_explicit_provider_and_model(self):
        sel = resolve_provider("anthropic", "claude-3-haiku-20240307")
        self.assertEqual(sel.provider, "anthropic")
        self.assertEqual(sel.model, "claude-3-haiku-20240307")

    def test_falls_back_to_provider_default_model(self):
        sel = resolve_provider("openai", None)
        self.assertEqual(sel.model, DEFAULT_MODELS["openai"])

    def test_unsupported_provider_raises(self):
        with self.assertRaises(ValueError):
            resolve_provider("unsupported_provider")

    def test_all_four_providers_resolvable(self):
        for provider in ("anthropic", "openai", "google", "groq"):
            sel = resolve_provider(provider)
            self.assertEqual(sel.provider, provider)
            self.assertEqual(sel.model, DEFAULT_MODELS[provider])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_response(text: str = "Generated briefing."):
    """Build a minimal mock response object with a .text or .content[0].text."""
    resp = MagicMock()
    # Anthropic-style
    cb = MagicMock()
    cb.text = text
    usage = MagicMock()
    usage.output_tokens = len(text.split())
    resp.content = [cb]
    resp.usage = usage
    # OpenAI / Groq-style
    choice = MagicMock()
    choice.message.content = text
    resp.choices = [choice]
    # Google-style
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class TestCallAnthropic(unittest.TestCase):
    @patch("src.llm_providers.anthropic")
    def test_returns_model_text(self, mock_ant):
        mock_ant.Anthropic.return_value.messages.create.return_value = _fake_response("Anthropic result")
        result = generate_text("prompt", provider="anthropic", max_retries=1)
        self.assertEqual(result, "Anthropic result")

    @patch("src.llm_providers.anthropic")
    def test_passes_temperature_and_max_tokens(self, mock_ant):
        mock_ant.Anthropic.return_value.messages.create.return_value = _fake_response()
        generate_text("prompt", provider="anthropic", temperature=0.5, max_tokens=512, max_retries=1)
        _, kwargs = mock_ant.Anthropic.return_value.messages.create.call_args
        self.assertAlmostEqual(kwargs["temperature"], 0.5)
        self.assertEqual(kwargs["max_tokens"], 512)

    @patch("src.llm_providers.anthropic")
    def test_uses_defaults_when_none(self, mock_ant):
        mock_ant.Anthropic.return_value.messages.create.return_value = _fake_response()
        generate_text("prompt", provider="anthropic", max_retries=1)
        _, kwargs = mock_ant.Anthropic.return_value.messages.create.call_args
        self.assertAlmostEqual(kwargs["temperature"], _DEFAULT_TEMPERATURE)
        self.assertEqual(kwargs["max_tokens"], _DEFAULT_MAX_TOKENS)

    @patch("src.llm_providers.time.sleep")
    @patch("src.llm_providers.anthropic")
    def test_retries_on_rate_limit_then_succeeds(self, mock_ant, mock_sleep):
        mock_ant.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_ant.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_ant.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 429})
        mock_ant.Anthropic.return_value.messages.create.side_effect = [
            mock_ant.RateLimitError("rate limited"),
            _fake_response("ok after retry"),
        ]
        result = generate_text("prompt", provider="anthropic", max_retries=3)
        self.assertEqual(result, "ok after retry")
        mock_sleep.assert_called_once()

    @patch("src.llm_providers.time.sleep")
    @patch("src.llm_providers.anthropic")
    def test_raises_runtime_error_after_all_retries(self, mock_ant, mock_sleep):
        mock_ant.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_ant.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_ant.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 429})
        mock_ant.Anthropic.return_value.messages.create.side_effect = (
            mock_ant.RateLimitError("always fails")
        )
        with self.assertRaises(RuntimeError) as cm:
            generate_text("prompt", provider="anthropic", max_retries=2)
        self.assertIn("2 attempt(s)", str(cm.exception))


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class TestCallOpenAI(unittest.TestCase):
    @patch("src.llm_providers.openai")
    def test_returns_model_text(self, mock_oai):
        mock_oai.OpenAI.return_value.chat.completions.create.return_value = _fake_response("OpenAI result")
        result = generate_text("prompt", provider="openai", max_retries=1)
        self.assertEqual(result, "OpenAI result")

    @patch("src.llm_providers.openai")
    def test_passes_temperature_and_max_tokens(self, mock_oai):
        mock_oai.OpenAI.return_value.chat.completions.create.return_value = _fake_response()
        generate_text("prompt", provider="openai", temperature=0.7, max_tokens=2048, max_retries=1)
        _, kwargs = mock_oai.OpenAI.return_value.chat.completions.create.call_args
        self.assertAlmostEqual(kwargs["temperature"], 0.7)
        self.assertEqual(kwargs["max_tokens"], 2048)

    @patch("src.llm_providers.time.sleep")
    @patch("src.llm_providers.openai")
    def test_retries_on_rate_limit(self, mock_oai, mock_sleep):
        mock_oai.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_oai.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_oai.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 429})
        mock_oai.OpenAI.return_value.chat.completions.create.side_effect = [
            mock_oai.RateLimitError("rate limited"),
            _fake_response("ok"),
        ]
        result = generate_text("prompt", provider="openai", max_retries=3)
        self.assertEqual(result, "ok")

    @patch("src.llm_providers.time.sleep")
    @patch("src.llm_providers.openai")
    def test_raises_runtime_error_after_all_retries(self, mock_oai, mock_sleep):
        mock_oai.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_oai.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_oai.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 429})
        mock_oai.OpenAI.return_value.chat.completions.create.side_effect = (
            mock_oai.RateLimitError("always fails")
        )
        with self.assertRaises(RuntimeError):
            generate_text("prompt", provider="openai", max_retries=2)


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

class TestCallGoogle(unittest.TestCase):
    @patch("src.llm_providers.genai_types")
    @patch("src.llm_providers.genai")
    def test_returns_model_text(self, mock_genai, mock_types):
        mock_genai.Client.return_value.models.generate_content.return_value = _fake_response("Google result")
        mock_types.GenerateContentConfig.return_value = MagicMock()
        result = generate_text("prompt", provider="google", max_retries=1)
        self.assertEqual(result, "Google result")

    @patch("src.llm_providers.genai_types")
    @patch("src.llm_providers.genai")
    def test_passes_temperature_and_max_tokens(self, mock_genai, mock_types):
        mock_genai.Client.return_value.models.generate_content.return_value = _fake_response()
        generate_text("prompt", provider="google", temperature=0.3, max_tokens=1024, max_retries=1)
        mock_types.GenerateContentConfig.assert_called_once_with(
            temperature=0.3,
            max_output_tokens=1024,
        )

    @patch("src.llm_providers.genai_types")
    @patch("src.llm_providers.genai")
    def test_uses_model_from_config(self, mock_genai, mock_types):
        mock_genai.Client.return_value.models.generate_content.return_value = _fake_response()
        generate_text("prompt", provider="google", model="gemini-2.5-pro", max_retries=1)
        _, kwargs = mock_genai.Client.return_value.models.generate_content.call_args
        self.assertEqual(kwargs["model"], "gemini-2.5-pro")


# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------

class TestCallGroq(unittest.TestCase):
    @patch("src.llm_providers.groq")
    def test_returns_model_text(self, mock_groq):
        mock_groq.Groq.return_value.chat.completions.create.return_value = _fake_response("Groq result")
        result = generate_text("prompt", provider="groq", max_retries=1)
        self.assertEqual(result, "Groq result")

    @patch("src.llm_providers.groq")
    def test_passes_temperature_and_max_tokens(self, mock_groq):
        mock_groq.Groq.return_value.chat.completions.create.return_value = _fake_response()
        generate_text("prompt", provider="groq", temperature=0.1, max_tokens=3000, max_retries=1)
        _, kwargs = mock_groq.Groq.return_value.chat.completions.create.call_args
        self.assertAlmostEqual(kwargs["temperature"], 0.1)
        self.assertEqual(kwargs["max_tokens"], 3000)

    @patch("src.llm_providers.time.sleep")
    @patch("src.llm_providers.groq")
    def test_retries_on_rate_limit(self, mock_groq, mock_sleep):
        mock_groq.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_groq.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_groq.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 429})
        mock_groq.Groq.return_value.chat.completions.create.side_effect = [
            mock_groq.RateLimitError("rate limited"),
            _fake_response("ok"),
        ]
        result = generate_text("prompt", provider="groq", max_retries=3)
        self.assertEqual(result, "ok")

    @patch("src.llm_providers.time.sleep")
    @patch("src.llm_providers.groq")
    def test_raises_runtime_error_after_all_retries(self, mock_groq, mock_sleep):
        mock_groq.RateLimitError = type("RateLimitError", (Exception,), {})
        mock_groq.APIConnectionError = type("APIConnectionError", (Exception,), {})
        mock_groq.APIStatusError = type("APIStatusError", (Exception,), {"status_code": 429})
        mock_groq.Groq.return_value.chat.completions.create.side_effect = (
            mock_groq.RateLimitError("always fails")
        )
        with self.assertRaises(RuntimeError):
            generate_text("prompt", provider="groq", max_retries=2)


if __name__ == "__main__":
    unittest.main()
