from __future__ import annotations

import logging
from datetime import date
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, create_model

logger = logging.getLogger(__name__)


REQUIRED_MANIFEST_KEYS = {"version", "environment", "files"}

REQUIRED_FILES = {"vendor_master", "purchase_orders", "vendor_performance"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "data" / "schemas"


ColumnType = Literal["string", "integer", "numeric", "date"]


class ColumnConstraintModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: Optional[float] = None
    max: Optional[float] = None


class DatasetSchemaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    primary_key: list[str] = []
    required_columns: list[str]
    optional_columns: list[str] = []
    column_types: dict[str, ColumnType]
    nullable: dict[str, bool] = {}
    enum_values: dict[str, list[Any]] = {}
    constraints: dict[str, ColumnConstraintModel] = {}

    def field_type_for(self, column: str) -> type[Any]:
        declared_type = self.column_types[column]
        mapping: dict[str, type[Any]] = {
            "string": str,
            "integer": int,
            "numeric": float,
            "date": date,
        }
        return mapping[declared_type]


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
    missing_keys = sorted(REQUIRED_MANIFEST_KEYS - public_keys)
    errors = [f"Missing manifest key: {key}" for key in missing_keys]

    if not errors:
        declared_files = set(manifest["files"])
        missing_files = sorted(REQUIRED_FILES - declared_files)
        errors.extend(f"Missing required file in manifest: {name}" for name in missing_files)

    result = ValidationResult(errors=errors)
    if result.has_errors:
        logger.error("Manifest shape validation failed: %s", result.errors)
    else:
        logger.debug("Manifest shape validation passed.")
    return result


def load_dataset_schema(dataset_name: str) -> dict[str, Any]:
    """Load a dataset schema YAML file by manifest dataset name."""
    return load_dataset_schema_model(dataset_name).model_dump(mode="python")


def load_dataset_schema_model(dataset_name: str) -> DatasetSchemaModel:
    """Load and validate a dataset schema YAML file with Pydantic."""
    schema_path = SCHEMA_DIR / f"{dataset_name}.schema.yaml"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found for dataset '{dataset_name}': {schema_path}")

    with schema_path.open("r", encoding="utf-8") as handle:
        schema = yaml.safe_load(handle)

    if not isinstance(schema, dict):
        raise ValueError(f"Schema file for dataset '{dataset_name}' must be a YAML mapping.")

    try:
        return DatasetSchemaModel.model_validate(schema)
    except ValidationError as exc:
        raise ValueError(
            f"Schema file for dataset '{dataset_name}' failed Pydantic validation: {exc}"
        ) from exc


def validate_dataset_frame(dataset_name: str, df: pd.DataFrame) -> ValidationResult:
    """Validate a dataset DataFrame against its schema definition."""
    schema = load_dataset_schema_model(dataset_name)
    errors: list[str] = []

    required_columns = schema.required_columns
    optional_columns = schema.optional_columns
    column_types = schema.column_types
    nullable = schema.nullable
    enum_values = schema.enum_values
    constraints = {
        column: constraint.model_dump(exclude_none=True)
        for column, constraint in schema.constraints.items()
    }

    expected_columns = set(required_columns) | set(optional_columns)
    row_model = _build_dataset_row_model(schema)

    for column in required_columns:
        if column not in df.columns:
            errors.append(f"Missing required column: {column}")

    present_columns = [column for column in df.columns if column in expected_columns]
    if missing_required := [column for column in required_columns if column not in df.columns]:
        logger.debug(
            "Skipping row-model validation for '%s'; missing required columns=%s",
            dataset_name,
            missing_required,
        )
    else:
        errors.extend(_validate_rows_with_pydantic(row_model, present_columns, df))

    for column in present_columns:
        column_series = df[column]
        null_mask = column_series.isna()
        if not nullable.get(column, False) and null_mask.any():
            for row_idx in column_series[null_mask].index.tolist():
                errors.append(f"Row {row_idx + 2}: column '{column}' is null but not nullable")

        non_null_series = column_series[~null_mask]
        if non_null_series.empty:
            continue

        declared_type = column_types.get(column)
        errors.extend(_validate_column_type(column, declared_type, non_null_series))
        errors.extend(_validate_column_enum(column, non_null_series, enum_values))
        errors.extend(_validate_column_constraints(column, non_null_series, constraints))

    errors.extend(_validate_dataset_specific_rules(dataset_name, df))

    result = ValidationResult(errors=errors)
    if result.has_errors:
        logger.error("Dataset validation failed for '%s': %s", dataset_name, result.errors)
    else:
        logger.debug("Dataset validation passed for '%s'.", dataset_name)
    return result


def _build_dataset_row_model(schema: DatasetSchemaModel) -> type[BaseModel]:
    fields: dict[str, tuple[Any, Any]] = {}
    for column in schema.required_columns + schema.optional_columns:
        base_type = schema.field_type_for(column)
        if column in schema.required_columns and not schema.nullable.get(column, False):
            fields[column] = (base_type, ...)
        else:
            fields[column] = (Optional[base_type], None)

    return create_model(
        f"{schema.name.title().replace('_', '')}RowModel",
        __config__=ConfigDict(extra="ignore"),
        **fields,
    )


def _validate_rows_with_pydantic(
    row_model: type[BaseModel],
    present_columns: list[str],
    df: pd.DataFrame,
) -> list[str]:
    errors: list[str] = []
    for row_idx, (_, row) in enumerate(df[present_columns].iterrows()):
        payload = {
            column: (None if pd.isna(value) else value)
            for column, value in row.to_dict().items()
        }
        try:
            row_model.model_validate(payload)
        except ValidationError as exc:
            for issue in exc.errors():
                loc = issue.get("loc", ())
                column = str(loc[0]) if loc else "<row>"
                errors.append(
                    f"Row {row_idx + 2}: column '{column}' failed Pydantic validation ({issue['msg']})"
                )
    return errors


def _validate_column_type(
    column: str,
    declared_type: str | None,
    series: pd.Series,
) -> list[str]:
    errors: list[str] = []
    if declared_type in {"string", None}:
        return errors

    if declared_type == "integer":
        coerced = pd.to_numeric(series, errors="coerce")
        invalid_mask = coerced.isna() | (coerced % 1 != 0)
    elif declared_type == "numeric":
        coerced = pd.to_numeric(series, errors="coerce")
        invalid_mask = coerced.isna()
    elif declared_type == "date":
        coerced = pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")
        invalid_mask = coerced.isna()
    else:
        return errors

    for row_idx, raw_value in series[invalid_mask].items():
        errors.append(
            f"Row {row_idx + 2}: column '{column}' has invalid {declared_type} value {raw_value!r}"
        )
    return errors


def _validate_column_enum(
    column: str,
    series: pd.Series,
    enum_values: dict[str, list[Any]],
) -> list[str]:
    if column not in enum_values:
        return []

    allowed = set(enum_values[column])
    errors: list[str] = []
    for row_idx, raw_value in series.items():
        if raw_value not in allowed:
            errors.append(
                f"Row {row_idx + 2}: column '{column}' has invalid value {raw_value!r}; "
                f"expected one of {sorted(allowed)!r}"
            )
    return errors


def _validate_column_constraints(
    column: str,
    series: pd.Series,
    constraints: dict[str, dict[str, Any]],
) -> list[str]:
    if column not in constraints:
        return []

    column_constraints = constraints[column]
    coerced = pd.to_numeric(series, errors="coerce")
    errors: list[str] = []

    if "min" in column_constraints:
        min_value = column_constraints["min"]
        for row_idx, numeric_value in coerced[coerced < min_value].items():
            errors.append(
                f"Row {row_idx + 2}: column '{column}' value {numeric_value!r} is below minimum {min_value}"
            )

    if "max" in column_constraints:
        max_value = column_constraints["max"]
        for row_idx, numeric_value in coerced[coerced > max_value].items():
            errors.append(
                f"Row {row_idx + 2}: column '{column}' value {numeric_value!r} exceeds maximum {max_value}"
            )

    return errors


def _validate_dataset_specific_rules(dataset_name: str, df: pd.DataFrame) -> list[str]:
    if dataset_name != "vendor_performance":
        return []

    if "metric_uom" not in df.columns or "metric_value" not in df.columns:
        return []

    errors: list[str] = []
    pct_rows = df["metric_uom"] == "pct"
    coerced_values = pd.to_numeric(df.loc[pct_rows, "metric_value"], errors="coerce")
    invalid_mask = coerced_values.isna() | (coerced_values < 0) | (coerced_values > 1)

    for row_idx, numeric_value in coerced_values[invalid_mask].items():
        errors.append(
            f"Row {row_idx + 2}: column 'metric_value' must be between 0 and 1 when metric_uom is 'pct'; got {numeric_value!r}"
        )

    return errors
