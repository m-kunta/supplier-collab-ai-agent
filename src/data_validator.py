from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


REQUIRED_MANIFEST_KEYS = {"version", "environment", "files"}


@dataclass
class ValidationResult:
    """Holds the outcome of a validation pass with severity-separated messages.

    Errors are fatal — they indicate the pipeline cannot proceed safely.
    Warnings are non-fatal — they indicate missing optional data or stale
    freshness, and result in degraded (but still valid) briefing sections.
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """True when at least one fatal error is present."""
        return bool(self.errors)

    @property
    def is_valid(self) -> bool:
        """True when no fatal errors are present (warnings are allowed)."""
        return not self.errors

    def __repr__(self) -> str:
        return (
            f"ValidationResult(errors={len(self.errors)}, "
            f"warnings={len(self.warnings)}, "
            f"is_valid={self.is_valid})"
        )


def validate_manifest_shape(manifest: dict[str, Any]) -> ValidationResult:
    """Check that the manifest contains all required top-level keys.

    Private keys injected by ``load_manifest()`` (prefixed with ``_``) are
    excluded from the comparison so they do not interfere with validation.

    Args:
        manifest: Parsed manifest dict, optionally enriched by ``load_manifest()``.

    Returns:
        A :class:`ValidationResult`. Missing required keys are reported as
        *errors* (fatal). No warnings are produced at this validation stage;
        optional-file freshness checks will be added in Phase 2.
    """
    public_keys = {k for k in manifest if not k.startswith("_")}
    missing = sorted(REQUIRED_MANIFEST_KEYS - public_keys)
    errors = [f"Missing manifest key: {key}" for key in missing]
    result = ValidationResult(errors=errors)
    if result.has_errors:
        logger.error("Manifest shape validation failed: %s", result.errors)
    else:
        logger.debug("Manifest shape validation passed.")
    return result
