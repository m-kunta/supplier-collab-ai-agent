from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "agent_config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config is None:
        raise ValueError(f"Config file at {path} is empty or invalid.")
    if not isinstance(config, dict):
        raise ValueError(f"Config file at {path} must be a YAML mapping (dictionary).")
    return config
