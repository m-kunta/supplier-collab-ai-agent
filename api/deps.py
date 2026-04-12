from __future__ import annotations

from pathlib import Path

# Repository root (parent of the `api/` package).
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_data_dir(path_str: str) -> Path:
    """Resolve a landing-zone path for API requests.

    Relative paths are anchored to the repository root so the server behaves
    consistently regardless of the process working directory.
    """
    p = Path(path_str)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p
