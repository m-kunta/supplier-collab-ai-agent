from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd


def _parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _empty_result() -> dict[str, Any]:
    return {
        "week_count": 0,
        "sku_count": 0,
        "location_count": 0,
        "avg_forecast_accuracy_pct": None,
        "avg_forecast_bias": None,
        "underforecasted_week_count": 0,
        "overforecasted_week_count": 0,
        "promo_period_accuracy_pct": None,
        "non_promo_period_accuracy_pct": None,
        "largest_underforecast_skus": [],
    }


def compute_forecast_insights(
    vendor_id: str,
    forecast_df: pd.DataFrame,
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    _ = vendor_id
    ref_date = reference_date or date.today()
    if forecast_df.empty:
        return _empty_result()

    forecast = forecast_df.copy()
    forecast["week_ending_parsed"] = forecast.get(
        "week_ending",
        pd.Series([None] * len(forecast), index=forecast.index),
    ).apply(_parse_date)
    forecast = forecast[forecast["week_ending_parsed"].notna()].copy()
    forecast = forecast[forecast["week_ending_parsed"] <= ref_date].copy()
    if forecast.empty:
        return _empty_result()

    forecast["forecast_qty_num"] = pd.to_numeric(forecast.get("forecast_qty"), errors="coerce")
    forecast["actual_qty_num"] = pd.to_numeric(forecast.get("actual_qty"), errors="coerce")

    derived_accuracy = 1 - (
        (forecast["actual_qty_num"] - forecast["forecast_qty_num"]).abs()
        / forecast["actual_qty_num"].replace(0, pd.NA)
    )
    derived_bias = (
        (forecast["forecast_qty_num"] - forecast["actual_qty_num"])
        / forecast["actual_qty_num"].replace(0, pd.NA)
    )

    accuracy_source = forecast.get(
        "forecast_accuracy_pct",
        pd.Series([pd.NA] * len(forecast), index=forecast.index),
    )
    bias_source = forecast.get(
        "forecast_bias",
        pd.Series([pd.NA] * len(forecast), index=forecast.index),
    )
    forecast["accuracy"] = pd.to_numeric(accuracy_source, errors="coerce").fillna(
        derived_accuracy
    )
    forecast["bias"] = pd.to_numeric(bias_source, errors="coerce").fillna(derived_bias)

    promo_mask = forecast.get(
        "is_promo_period",
        pd.Series([False] * len(forecast), index=forecast.index),
    ).fillna(False).astype(bool)

    underforecast = forecast[
        forecast["actual_qty_num"].notna()
        & forecast["forecast_qty_num"].notna()
        & (forecast["actual_qty_num"] > forecast["forecast_qty_num"])
    ].copy()
    if underforecast.empty:
        largest_underforecast_skus: list[dict[str, Any]] = []
    else:
        underforecast["shortfall_qty"] = (
            underforecast["actual_qty_num"] - underforecast["forecast_qty_num"]
        )
        grouped = (
            underforecast.groupby("sku", dropna=True)["shortfall_qty"]
            .sum()
            .sort_values(ascending=False)
        )
        largest_underforecast_skus = [
            {"sku": str(sku), "shortfall_qty": float(shortfall)}
            for sku, shortfall in grouped.head(5).items()
        ]

    def _mean_or_none(series: pd.Series) -> float | None:
        clean = pd.to_numeric(series, errors="coerce").dropna()
        if clean.empty:
            return None
        return round(float(clean.mean()), 4)

    return {
        "week_count": int(len(forecast)),
        "sku_count": int(forecast["sku"].dropna().astype(str).nunique()) if "sku" in forecast.columns else 0,
        "location_count": int(forecast["location_id"].dropna().astype(str).nunique()) if "location_id" in forecast.columns else 0,
        "avg_forecast_accuracy_pct": _mean_or_none(forecast["accuracy"]),
        "avg_forecast_bias": _mean_or_none(forecast["bias"]),
        "underforecasted_week_count": int((forecast["bias"] < 0).fillna(False).sum()),
        "overforecasted_week_count": int((forecast["bias"] > 0).fillna(False).sum()),
        "promo_period_accuracy_pct": _mean_or_none(forecast.loc[promo_mask, "accuracy"]),
        "non_promo_period_accuracy_pct": _mean_or_none(forecast.loc[~promo_mask, "accuracy"]),
        "largest_underforecast_skus": largest_underforecast_skus,
    }
