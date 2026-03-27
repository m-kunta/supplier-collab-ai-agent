from __future__ import annotations

import os
from dataclasses import dataclass


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
    return ProviderSelection(provider=provider, model=model)


def generate_text(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    selection = resolve_provider(provider, model)
    return (
        "LLM generation is not implemented in the scaffold. "
        f"Selected provider={selection.provider}, model={selection.model}, prompt_chars={len(prompt)}."
    )
