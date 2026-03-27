from __future__ import annotations

from typing import Any


REQUIRED_MANIFEST_KEYS = {"version", "environment", "files"}


def validate_manifest_shape(manifest: dict[str, Any]) -> list[str]:
    missing = sorted(REQUIRED_MANIFEST_KEYS - set(manifest))
    return [f"Missing manifest key: {key}" for key in missing]
