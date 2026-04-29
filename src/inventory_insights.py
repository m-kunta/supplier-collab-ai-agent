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
        "snapshot_date": None,
        "sku_count": 0,
        "location_count": 0,
        "total_on_hand_qty": 0.0,
        "total_allocated_qty": 0.0,
        "total_in_transit_qty": 0.0,
        "total_on_order_qty": 0.0,
        "low_days_of_supply_sku_count": 0,
        "low_days_of_supply_skus": [],
        "promo_at_risk_count": 0,
        "promo_at_risk_events": [],
    }


def compute_inventory_insights(
    vendor_id: str,
    inventory_df: pd.DataFrame,
    promo_df: pd.DataFrame,
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    _ = vendor_id
    ref_date = reference_date or date.today()

    if inventory_df.empty:
        return _empty_result()

    inventory = inventory_df.copy()
    inventory["qty_on_hand"] = pd.to_numeric(inventory.get("qty_on_hand"), errors="coerce").fillna(0.0)
    inventory["qty_allocated"] = pd.to_numeric(inventory.get("qty_allocated"), errors="coerce").fillna(0.0)
    inventory["qty_in_transit"] = pd.to_numeric(inventory.get("qty_in_transit"), errors="coerce").fillna(0.0)
    inventory["qty_on_order"] = pd.to_numeric(inventory.get("qty_on_order"), errors="coerce").fillna(0.0)
    inventory["days_of_supply_num"] = pd.to_numeric(
        inventory.get("days_of_supply"), errors="coerce"
    )
    inventory["snapshot_date_parsed"] = inventory.get(
        "snapshot_date",
        pd.Series([None] * len(inventory), index=inventory.index),
    ).apply(_parse_date)

    sku_summary = (
        inventory.groupby("sku", dropna=True)
        .agg(
            qty_on_hand=("qty_on_hand", "sum"),
            qty_in_transit=("qty_in_transit", "sum"),
            qty_on_order=("qty_on_order", "sum"),
            days_of_supply=("days_of_supply_num", "min"),
        )
        .reset_index()
    )

    low_cover = (
        sku_summary[sku_summary["days_of_supply"].notna() & (sku_summary["days_of_supply"] < 7)]
        .sort_values(["days_of_supply", "sku"], ascending=[True, True])
    )
    low_cover_skus = [
        {
            "sku": str(row["sku"]),
            "days_of_supply": float(row["days_of_supply"]),
            "qty_on_hand": float(row["qty_on_hand"]),
        }
        for _, row in low_cover.head(5).iterrows()
    ]

    promo_at_risk_events: list[dict[str, Any]] = []
    if not promo_df.empty and "sku" in promo_df.columns:
        promo = promo_df.copy()
        promo["inventory_need_date_parsed"] = promo.get(
            "inventory_need_date",
            pd.Series([None] * len(promo), index=promo.index),
        ).apply(_parse_date)
        promo["committed_qty_num"] = pd.to_numeric(
            promo.get("committed_qty"), errors="coerce"
        ).fillna(0.0)
        future_promo = promo[promo["inventory_need_date_parsed"].notna()]
        future_promo = future_promo[future_promo["inventory_need_date_parsed"] >= ref_date]

        sku_lookup = sku_summary.set_index("sku").to_dict("index")
        for _, row in future_promo.iterrows():
            sku = str(row["sku"])
            summary = sku_lookup.get(sku)
            if summary is None:
                continue
            total_supply = float(summary["qty_on_hand"] + summary["qty_in_transit"] + summary["qty_on_order"])
            reasons: list[str] = []
            dos = summary["days_of_supply"]
            if pd.notna(dos) and float(dos) < 7:
                reasons.append("low_days_of_supply")
            if total_supply < float(row["committed_qty_num"]):
                reasons.append("insufficient_total_supply")
            if reasons:
                promo_at_risk_events.append(
                    {
                        "promo_event_id": str(row.get("promo_event_id", "")),
                        "promo_name": str(row.get("promo_name", "")),
                        "sku": sku,
                        "inventory_need_date": row["inventory_need_date_parsed"].isoformat(),
                        "committed_qty": float(row["committed_qty_num"]),
                        "total_supply_qty": total_supply,
                        "risk_reasons": reasons,
                    }
                )

    snapshot_dates = inventory["snapshot_date_parsed"].dropna()
    snapshot_date = snapshot_dates.max().isoformat() if not snapshot_dates.empty else None

    return {
        "snapshot_date": snapshot_date,
        "sku_count": int(inventory["sku"].dropna().astype(str).nunique()) if "sku" in inventory.columns else 0,
        "location_count": int(inventory["location_id"].dropna().astype(str).nunique()) if "location_id" in inventory.columns else 0,
        "total_on_hand_qty": float(inventory["qty_on_hand"].sum()),
        "total_allocated_qty": float(inventory["qty_allocated"].sum()),
        "total_in_transit_qty": float(inventory["qty_in_transit"].sum()),
        "total_on_order_qty": float(inventory["qty_on_order"].sum()),
        "low_days_of_supply_sku_count": int(len(low_cover)),
        "low_days_of_supply_skus": low_cover_skus,
        "promo_at_risk_count": int(len(promo_at_risk_events)),
        "promo_at_risk_events": promo_at_risk_events,
    }
