from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Module-level optional imports — each is None when the package is absent.
# This pattern lets @patch("src.llm_providers.<pkg>") work in tests without
# requiring all SDK packages to be installed.
# ---------------------------------------------------------------------------

try:
    import anthropic as anthropic  # noqa: PLC0415
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore[assignment]

try:
    import openai as openai  # noqa: PLC0415
except ImportError:  # pragma: no cover
    openai = None  # type: ignore[assignment]

try:
    from google import genai as genai  # noqa: PLC0415
    from google.genai import types as genai_types  # noqa: PLC0415
except ImportError:  # pragma: no cover
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

try:
    import groq as groq  # noqa: PLC0415
except ImportError:  # pragma: no cover
    groq = None  # type: ignore[assignment]

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

# Default generation parameters — overridden by config / caller arguments.
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_TOKENS = 4096

# Exponential back-off: base sleep in seconds between retry attempts.
_RETRY_BASE_DELAY_S = 1.0


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


# ---------------------------------------------------------------------------
# Shared retry helper
# ---------------------------------------------------------------------------

def _retry_loop(
    fn,
    *,
    max_retries: int,
    provider_name: str,
    retryable_exc_types: tuple,
    server_error_exc_type=None,
    get_status_code=None,
):
    """Execute *fn()* up to *max_retries* times with exponential back-off.

    Args:
        fn: Zero-arg callable that performs the API call and returns the
            generated text string.
        max_retries: Maximum number of attempts.
        provider_name: Used in log/error messages only.
        retryable_exc_types: Tuple of exception types that trigger a retry
            (e.g. RateLimitError, APIConnectionError).
        server_error_exc_type: Optional exception type for HTTP status errors.
            When provided, retries on status >= 500 and re-raises on 4xx.
        get_status_code: Callable(exc) → int, required when
            *server_error_exc_type* is given.

    Returns:
        Generated text string from the first successful attempt.

    Raises:
        RuntimeError: When all retries are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            result = fn()
            logger.info("%s API call succeeded (attempt=%d).", provider_name, attempt)
            return result

        except Exception as exc:  # noqa: BLE001
            exc_type = type(exc)

            # Server-error branch (e.g. APIStatusError with status >= 500)
            if server_error_exc_type and isinstance(exc, server_error_exc_type):
                status = get_status_code(exc) if get_status_code else None
                if status is not None and status >= 500:
                    last_error = exc
                    delay = _RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                    logger.warning(
                        "%s server error %d (attempt %d/%d). Retrying in %.1fs.",
                        provider_name, status, attempt, max_retries, delay,
                    )
                    if attempt < max_retries:
                        time.sleep(delay)
                    continue
                else:
                    raise  # 4xx — not retriable

            # Retryable transient errors
            if isinstance(exc, retryable_exc_types):
                last_error = exc
                delay = _RETRY_BASE_DELAY_S * (2 ** (attempt - 1))
                logger.warning(
                    "%s transient error (attempt %d/%d). Retrying in %.1fs. Error: %s",
                    provider_name, attempt, max_retries, delay, exc,
                )
                if attempt < max_retries:
                    time.sleep(delay)
                continue

            raise  # Non-retriable — propagate immediately

    raise RuntimeError(
        f"{provider_name} API call failed after {max_retries} attempt(s). "
        f"Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _call_anthropic(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    """Call the Anthropic Messages API with exponential back-off retry.

    Reads ``ANTHROPIC_API_KEY`` from the environment.

    Args:
        prompt: Full assembled prompt string.
        model: Anthropic model identifier (e.g. ``'claude-3-5-sonnet-latest'``).
        temperature: Sampling temperature (0.0–1.0).
        max_tokens: Maximum tokens to generate.
        max_retries: Number of retry attempts on transient errors.

    Returns:
        Generated text string from the model.

    Raises:
        ImportError: If the ``anthropic`` package is not installed.
        RuntimeError: If all retries are exhausted.
    """
    try:
        import anthropic as _anthropic  # local fallback when top-level is None
        _ant = _anthropic
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required. Run: pip install 'anthropic>=0.34.0'"
        ) from exc

    # Use the module-level import when available (supports @patch in tests).
    if anthropic is not None:
        _ant = anthropic

    client = _ant.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    logger.info(
        "Anthropic API call: model=%s, max_tokens=%d, max_retries=%d.",
        model, max_tokens, max_retries,
    )

    def _call():
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    return _retry_loop(
        _call,
        max_retries=max_retries,
        provider_name="Anthropic",
        retryable_exc_types=(_ant.RateLimitError, _ant.APIConnectionError),
        server_error_exc_type=_ant.APIStatusError,
        get_status_code=lambda e: e.status_code,
    )


def _call_openai(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    """Call the OpenAI Chat Completions API with exponential back-off retry.

    Reads ``OPENAI_API_KEY`` from the environment.

    Args:
        prompt: Full assembled prompt string.
        model: OpenAI model identifier (e.g. ``'gpt-4o-mini'``).
        temperature: Sampling temperature (0.0–2.0 per OpenAI docs; keep ≤1.0).
        max_tokens: Maximum tokens to generate.
        max_retries: Number of retry attempts on transient errors.

    Returns:
        Generated text string from the model.

    Raises:
        ImportError: If the ``openai`` package is not installed.
        RuntimeError: If all retries are exhausted.
    """
    # Use the module-level import when available (patched in tests or installed);
    # fall back to a local import only when the module-level binding is None.
    if openai is not None:
        _oai = openai
    else:
        try:
            import openai as _openai_local
            _oai = _openai_local
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is required. Run: pip install 'openai>=1.0.0'"
            ) from exc

    client = _oai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    logger.info(
        "OpenAI API call: model=%s, max_tokens=%d, max_retries=%d.",
        model, max_tokens, max_retries,
    )

    def _call():
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    return _retry_loop(
        _call,
        max_retries=max_retries,
        provider_name="OpenAI",
        retryable_exc_types=(_oai.RateLimitError, _oai.APIConnectionError),
        server_error_exc_type=_oai.APIStatusError,
        get_status_code=lambda e: e.status_code,
    )


def _call_google(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    """Call the Google Gen AI API (``google-genai`` SDK) with exponential back-off retry.

    Reads ``GOOGLE_API_KEY`` from the environment.

    Uses the modern ``google-genai`` SDK (``genai.Client`` / ``client.models.generate_content``),
    not the legacy ``google-generativeai`` library.

    Args:
        prompt: Full assembled prompt string.
        model: Gemini model identifier (e.g. ``'gemini-2.5-flash'``).
        temperature: Sampling temperature (0.0–2.0 per Google docs; keep ≤1.0).
        max_tokens: Maximum output tokens to generate.
        max_retries: Number of retry attempts on transient errors.

    Returns:
        Generated text string from the model.

    Raises:
        ImportError: If the ``google-genai`` package is not installed.
        RuntimeError: If all retries are exhausted.
    """
    if genai is not None:
        _g = genai
        _t = genai_types
    else:
        try:
            from google import genai as _genai_local
            from google.genai import types as _types_local
            _g = _genai_local
            _t = _types_local
        except ImportError as exc:
            raise ImportError(
                "The 'google-genai' package is required. Run: pip install 'google-genai>=1.0.0'"
            ) from exc

    client = _g.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    logger.info(
        "Google Gen AI API call: model=%s, max_tokens=%d, max_retries=%d.",
        model, max_tokens, max_retries,
    )

    def _call():
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=_t.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    # google-genai raises google.api_core.exceptions for transient errors.
    try:
        from google.api_core import exceptions as _gapi_exc
        retryable = (_gapi_exc.ServiceUnavailable, _gapi_exc.DeadlineExceeded,
                     _gapi_exc.ResourceExhausted)
    except ImportError:  # pragma: no cover
        retryable = (Exception,)  # type: ignore[assignment]

    return _retry_loop(
        _call,
        max_retries=max_retries,
        provider_name="Google",
        retryable_exc_types=retryable,
    )


def _call_groq(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
) -> str:
    """Call the Groq Chat Completions API with exponential back-off retry.

    Reads ``GROQ_API_KEY`` from the environment. Groq offers OpenAI-compatible
    endpoints and extremely low-latency inference for open-source models.

    Args:
        prompt: Full assembled prompt string.
        model: Groq model identifier (e.g. ``'llama-3.3-70b-versatile'``).
        temperature: Sampling temperature (0.0–2.0; keep ≤1.0 for determinism).
        max_tokens: Maximum tokens to generate.
        max_retries: Number of retry attempts on transient errors.

    Returns:
        Generated text string from the model.

    Raises:
        ImportError: If the ``groq`` package is not installed.
        RuntimeError: If all retries are exhausted.
    """
    if groq is not None:
        _g = groq
    else:
        try:
            import groq as _groq_local
            _g = _groq_local
        except ImportError as exc:
            raise ImportError(
                "The 'groq' package is required. Run: pip install 'groq>=0.9.0'"
            ) from exc

    client = _g.Groq(api_key=os.getenv("GROQ_API_KEY"))

    logger.info(
        "Groq API call: model=%s, max_tokens=%d, max_retries=%d.",
        model, max_tokens, max_retries,
    )

    def _call():
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    return _retry_loop(
        _call,
        max_retries=max_retries,
        provider_name="Groq",
        retryable_exc_types=(_g.RateLimitError, _g.APIConnectionError),
        server_error_exc_type=_g.APIStatusError,
        get_status_code=lambda e: e.status_code,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_PROVIDER_DISPATCH = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
    "groq": _call_groq,
}


def generate_text(
    prompt: str,
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    max_retries: int = 3,
) -> str:
    """Generate text via the configured LLM provider.

    Supported providers: ``anthropic``, ``openai``, ``google``, ``groq``.

    Each provider requires its corresponding SDK to be installed and an API key
    in the environment (see ``.env.example``):

    .. code-block:: text

        anthropic  →  pip install 'anthropic>=0.34.0'   →  ANTHROPIC_API_KEY
        openai     →  pip install 'openai>=1.0.0'        →  OPENAI_API_KEY
        google     →  pip install 'google-genai>=1.0.0'  →  GOOGLE_API_KEY
        groq       →  pip install 'groq>=0.9.0'          →  GROQ_API_KEY

    Args:
        prompt: The full assembled prompt string to send to the LLM.
        provider: Override provider name. Falls back to ``LLM_PROVIDER`` env
            var then ``'anthropic'``.
        model: Override model name. Falls back to ``LLM_MODEL`` env var then
            the provider default from ``DEFAULT_MODELS``.
        temperature: Sampling temperature (0.0–1.0). Defaults to ``0.2``.
        max_tokens: Maximum tokens to generate. Defaults to ``4096``.
        max_retries: Retry attempts on transient API failures. Defaults to ``3``.

    Returns:
        Generated text string from the LLM.

    Raises:
        ValueError: If the resolved provider is not in ``DEFAULT_MODELS``.
        ImportError: If the required SDK package is not installed.
        RuntimeError: When all retry attempts are exhausted.
    """
    selection = resolve_provider(provider, model)
    resolved_temperature = temperature if temperature is not None else _DEFAULT_TEMPERATURE
    resolved_max_tokens = max_tokens if max_tokens is not None else _DEFAULT_MAX_TOKENS

    logger.info(
        "generate_text(): provider=%s, model=%s, prompt_chars=%d, "
        "temperature=%s, max_tokens=%d, max_retries=%d.",
        selection.provider, selection.model, len(prompt),
        resolved_temperature, resolved_max_tokens, max_retries,
    )

    caller = _PROVIDER_DISPATCH[selection.provider]
    return caller(
        prompt=prompt,
        model=selection.model,
        temperature=resolved_temperature,
        max_tokens=resolved_max_tokens,
        max_retries=max_retries,
    )
