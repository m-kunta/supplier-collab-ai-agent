from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import load_config
from src.data_loader import load_manifest
from src.data_validator import validate_manifest_shape
from src.llm_providers import resolve_provider


def summarize_request(
    *,
    vendor: str,
    meeting_date: str,
    data_dir: Path,
    lookback_weeks: int,
    persona_emphasis: str,
    include_benchmarks: bool,
    output_format: str,
    category_filter: str | None,
) -> dict[str, Any]:
    config = load_config()
    manifest = load_manifest(data_dir)
    validation_errors = validate_manifest_shape(manifest)
    provider = resolve_provider(
        config.get("llm", {}).get("default_provider"),
        config.get("llm", {}).get("default_model"),
    )
    return {
        "status": "scaffold",
        "message": "Briefing generation is not implemented yet.",
        "request": {
            "vendor": vendor,
            "meeting_date": meeting_date,
            "data_dir": str(data_dir),
            "lookback_weeks": lookback_weeks,
            "persona_emphasis": persona_emphasis,
            "include_benchmarks": include_benchmarks,
            "output_format": output_format,
            "category_filter": category_filter,
        },
        "config_defaults": config.get("defaults", {}),
        "llm_selection": {
            "provider": provider.provider,
            "model": provider.model,
        },
        "manifest_path": manifest.get("_manifest_path"),
        "available_file_keys": sorted(manifest.get("files", {}).keys()),
        "validation_errors": validation_errors,
    }
