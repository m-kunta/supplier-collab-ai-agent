from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSelection:
    provider: str
    model: str


DEFAULT_MODELS = {
    "anthropic": "claude-3-5-sonnet-latest",
    "openai": "gpt-4o-mini",
    "google": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
}


def resolve_provider(
    configured_provider: str | None = None,
    configured_model: str | None = None,
) -> ProviderSelection:
    provider = (configured_provider or os.getenv("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"Unsupported provider '{provider}' in scaffold.")
    model = configured_model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[provider]
    selection = ProviderSelection(provider=provider, model=model)
    logger.debug("Resolved LLM provider: %s / %s", selection.provider, selection.model)
    return selection


def generate_text(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_retries: int = 3,
) -> str:
    """Generate text via the configured LLM provider.

    Args:
        prompt: The full assembled prompt string to send to the LLM.
        provider: Override provider name (e.g. ``'anthropic'``). Falls back
            to ``LLM_PROVIDER`` env var then ``'anthropic'``.
        model: Override model name. Falls back to ``LLM_MODEL`` env var then
            the provider default.
        temperature: Sampling temperature (0.0–1.0). ``None`` defers to the
            value in ``agent_config.yaml`` (default ``0.2``).
        max_tokens: Maximum tokens to generate. ``None`` defers to the value
            in ``agent_config.yaml``. Set explicitly to cap output length.
        max_retries: Number of retry attempts on transient API failures.
            Defaults to ``3``. Will be used by the retry/backoff logic
            added in Phase 4.

    Returns:
        Generated text string from the LLM.

    Note:
        This function is a scaffold stub. Real API integration is implemented
        in Phase 4. Until then it returns a diagnostic string.
    """
    selection = resolve_provider(provider, model)
    logger.warning(
        "generate_text() called but LLM integration is not yet implemented "
        "(provider=%s, model=%s, prompt_chars=%d, temperature=%s, max_tokens=%s, max_retries=%d).",
        selection.provider, selection.model, len(prompt),
        temperature, max_tokens, max_retries,
    )
    return (
        "LLM generation is not implemented in the scaffold. "
        f"Selected provider={selection.provider}, model={selection.model}, "
        f"prompt_chars={len(prompt)}."
    )
