from __future__ import annotations

import unittest
from unittest.mock import patch

from src.llm_providers import generate_text_stream


class GenerateTextStreamFallbackTests(unittest.TestCase):
    @patch("src.llm_providers._PROVIDER_DISPATCH")
    def test_non_anthropic_stream_falls_back_to_single_chunk(self, mock_dispatch) -> None:
        mock_dispatch.__getitem__.return_value = lambda **_: "OpenAI full response"

        chunks = list(generate_text_stream("prompt", provider="openai", model="gpt-test"))

        self.assertEqual(chunks, ["OpenAI full response"])

    @patch("src.llm_providers._stream_anthropic")
    def test_anthropic_stream_yields_multiple_chunks(self, mock_stream) -> None:
        mock_stream.return_value = iter(["Hello ", "world"])

        chunks = list(generate_text_stream("prompt", provider="anthropic", model="claude-test"))

        self.assertEqual(chunks, ["Hello ", "world"])
