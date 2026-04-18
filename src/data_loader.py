from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def resolve_data_dir(data_dir: Path | str) -> Path:
    return Path(data_dir).expanduser().resolve()


def load_manifest(data_dir: Path) -> dict[str, Any]:
    """Load and parse ``manifest.yaml`` from the given data landing zone.

    Args:
        data_dir: Path to the landing zone directory containing ``manifest.yaml``.

    Returns:
        Parsed manifest dict enriched with two private keys:

        - ``_resolved_data_dir`` (str) — absolute path to the landing zone
        - ``_manifest_path`` (str) — absolute path to the manifest file

    Raises:
        FileNotFoundError: If ``manifest.yaml`` does not exist.
        ValueError: If the manifest is empty, non-YAML, or not a mapping.
    """
    resolved_dir = resolve_data_dir(data_dir)
    manifest_path = resolved_dir / "manifest.yaml"
    logger.debug("Loading manifest from %s", manifest_path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)

    if manifest is None:
        raise ValueError(f"Manifest file at {manifest_path} is empty or invalid.")
    if not isinstance(manifest, dict):
        raise ValueError(
            f"Manifest file at {manifest_path} must be a YAML mapping (dictionary)."
        )

    manifest["_resolved_data_dir"] = str(resolved_dir)
    manifest["_manifest_path"] = str(manifest_path)
    file_keys = sorted(manifest.get("files", {}).keys())
    logger.debug("Manifest loaded: env=%s, files=%s", manifest.get("environment"), file_keys)
    return manifest


def load_dataset(manifest: dict[str, Any], dataset_name: str) -> pd.DataFrame:
    """Load a single CSV file declared in the manifest.

    Args:
        manifest: Parsed manifest dict returned by :func:`load_manifest`.
            Must contain ``_resolved_data_dir`` and a ``files`` mapping with
            an entry for ``dataset_name``.
        dataset_name: Key in ``manifest["files"]`` (e.g. ``'vendor_master'``).

    Returns:
        A :class:`pandas.DataFrame` of the CSV contents with default dtypes.

    Raises:
        KeyError: If ``dataset_name`` is not declared in ``manifest["files"]``.
        FileNotFoundError: If the CSV file referenced by the manifest is missing.
    """
    files = manifest.get("files", {})
    if dataset_name not in files:
        raise KeyError(
            f"Dataset '{dataset_name}' is not declared in the manifest. "
            f"Available datasets: {sorted(files.keys())}"
        )

    data_dir = Path(manifest["_resolved_data_dir"])
    filename = files[dataset_name]["filename"]
    csv_path = data_dir / filename

    logger.debug("Loading dataset '%s' from %s", dataset_name, csv_path)
    df = pd.read_csv(csv_path)
    logger.debug("Dataset '%s' loaded: %d rows, %d columns", dataset_name, len(df), len(df.columns))
    return df


def load_vendor_data(
    manifest: dict[str, Any],
    vendor_id: str,
) -> dict[str, pd.DataFrame]:
    """Load all available manifest datasets and filter each to a single vendor.

    Only files declared in ``manifest["files"]`` are loaded. Files that are
    physically missing are skipped with no error — the caller should treat
    absent keys as missing optional data.

    Filtering is applied to any dataset that contains a ``vendor_id`` column.
    Datasets without that column are returned unfiltered (e.g. a future
    category-level reference table).

    Args:
        manifest: Parsed manifest dict returned by :func:`load_manifest`.
        vendor_id: Canonical vendor identifier to filter on (e.g. ``'V1001'``).

    Returns:
        Dict mapping dataset name → filtered :class:`pandas.DataFrame`.
        Only successfully loaded datasets are included.
    """
    result: dict[str, pd.DataFrame] = {}
    for dataset_name in manifest.get("files", {}):
        try:
            df = load_dataset(manifest, dataset_name)
        except FileNotFoundError:
            logger.warning(
                "Dataset '%s' declared in manifest but file not found — skipping section.",
                dataset_name,
            )
            continue

        if "vendor_id" in df.columns:
            pre_filter_count = len(df)
            df = df[df["vendor_id"] == vendor_id].reset_index(drop=True)
            logger.debug(
                "Filtered '%s' to vendor_id='%s': %d → %d rows",
                dataset_name, vendor_id, pre_filter_count, len(df),
            )

        result[dataset_name] = df

    logger.info(
        "Vendor data loaded for vendor_id='%s': %d dataset(s) available.",
        vendor_id, len(result),
    )
    return result


def resolve_vendor_id(vendor_input: str, vendor_master_df: pd.DataFrame) -> str:
    """Resolve a vendor name or canonical ID to a canonical ``vendor_id``.

    Accepts either the raw vendor ID (e.g. ``'V1001'``) or a vendor name
    (e.g. ``'Kelloggs'``). Name matching is case-insensitive and strips
    leading/trailing whitespace. If the input already matches a ``vendor_id``
    value exactly, it is returned as-is without consulting ``vendor_name``.

    Args:
        vendor_input: Vendor name as entered by the user, or a canonical
            ``vendor_id`` (e.g. from ``--vendor`` CLI arg).
        vendor_master_df: ``vendor_master`` DataFrame with at minimum columns
            ``[vendor_id, vendor_name]``.

    Returns:
        The canonical ``vendor_id`` string (e.g. ``'V1001'``).

    Raises:
        ValueError: If no match is found by ID or name, with a list of
            known vendor names to aid debugging.
    """
    stripped = vendor_input.strip()

    # Direct vendor_id match (exact, case-sensitive — IDs are canonical)
    if stripped in vendor_master_df["vendor_id"].values:
        logger.debug("vendor_input '%s' resolved as direct vendor_id match.", stripped)
        return stripped

    # Case-insensitive name match
    lower_input = stripped.lower()
    name_col = vendor_master_df["vendor_name"].str.strip().str.lower()
    matches = vendor_master_df[name_col == lower_input]

    if len(matches) == 1:
        resolved = matches.iloc[0]["vendor_id"]
        logger.debug(
            "vendor_input '%s' resolved by name match → vendor_id='%s'.",
            stripped, resolved,
        )
        return str(resolved)

    if len(matches) > 1:
        ids = matches["vendor_id"].tolist()
        raise ValueError(
            f"Vendor name '{stripped}' is ambiguous — matches multiple vendor IDs: {ids}. "
            "Please supply the canonical vendor_id directly."
        )

    known_names = sorted(vendor_master_df["vendor_name"].dropna().tolist())
    raise ValueError(
        f"Vendor '{stripped}' not found in vendor_master. "
        f"Known vendors: {known_names}"
    )
