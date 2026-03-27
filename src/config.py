from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "agent_config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
