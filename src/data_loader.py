from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any


def resolve_data_dir(data_dir: Path) -> Path:
    return data_dir.expanduser().resolve()


def load_manifest(data_dir: Path) -> dict[str, Any]:
    resolved_dir = resolve_data_dir(data_dir)
    manifest_path = resolved_dir / "manifest.yaml"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
        
    if manifest is None:
        raise ValueError(f"Manifest file at {manifest_path} is empty or invalid.")
    if not isinstance(manifest, dict):
        raise ValueError(f"Manifest file at {manifest_path} must be a YAML mapping (dictionary).")
        
    manifest["_resolved_data_dir"] = str(resolved_dir)
    manifest["_manifest_path"] = str(manifest_path)
    return manifest
