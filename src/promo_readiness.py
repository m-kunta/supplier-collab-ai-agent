from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def describe_scope() -> str:
    return (
        "Promo readiness engine: PO×promo coverage vs. promoted volume "
        "(on-time PO lines), volume-weighted scores, red/yellow/green tier."
    )


def _parse_date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _format_date(d: date | None) -> str:
    if d is None:
        return ""
    return d.isoformat()


def _risk_tier(score: float, red_threshold: float, yellow_threshold: float) -> str:
    if score < red_threshold:
        return "red"
    if score < yellow_threshold:
        return "yellow"
    return "green"


def _po_qty_on_time_for_start(
    po_df: pd.DataFrame,
    sku: str,
    promo_start: date,
) -> float:
    """Sum qty_ordered for PO lines matching sku that are not cancelled and
    have requested_delivery_date on or before promo_start (or missing date).
    """
    if po_df.empty or "sku" not in po_df.columns:
        return 0.0

    df = po_df[po_df["sku"].astype(str) == str(sku)]
    if df.empty:
        return 0.0

    statuses = (
        df.get("po_status", pd.Series(["open"] * len(df), index=df.index))
        .fillna("open")
        .astype(str)
        .str.lower()
        .str.strip()
    )
    df = df.loc[statuses != "cancelled"].copy()
    if df.empty:
        return 0.0

    qty_col = df.get("qty_ordered", pd.Series([0.0] * len(df), index=df.index))
    qty_col = pd.to_numeric(qty_col, errors="coerce").fillna(0.0)

    req = df.get(
        "requested_delivery_date",
        pd.Series([None] * len(df), index=df.index),
    )
    req_dates = req.apply(_parse_date)

    def counts(rqd: date | None) -> bool:
        if rqd is None:
            return True
        return rqd <= promo_start

    mask = req_dates.apply(counts)
    return float(qty_col.loc[mask].sum())


def compute_promo_readiness(
    vendor_id: str,
    promo_df: pd.DataFrame,
    po_df: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Score promotional readiness for a vendor's upcoming promotions.

    Each upcoming promo event is evaluated for PO coverage and fill-rate
    history to produce a per-event readiness score and an overall tier.

    Args:
        vendor_id: Canonical vendor identifier (e.g. ``'V1001'``).
        promo_df: ``promo_calendar`` DataFrame filtered to ``vendor_id``.
            Expected columns include
            ``[promo_id, event_name, start_date, end_date, sku, promoted_volume]``.
        po_df: ``purchase_orders`` DataFrame filtered to ``vendor_id``,
            used for PO × promo cross-reference to determine coverage.
        config: Full agent config dict; uses:

            - ``thresholds.promo_readiness_red_threshold`` — score below this → red
            - ``thresholds.promo_readiness_yellow_threshold`` — score below this → yellow

    Returns:
        Dict with:

        - ``overall_score`` (float) — composite readiness score from 0.0 to 1.0
        - ``risk_tier`` (str) — ``'red'``, ``'yellow'``, or ``'green'``
        - ``events`` (list[dict]) — one entry per promo event, each:
          ``{promo_id: str, event_name: str, start_date: str,
          score: float, covered_by_po: bool}``
    """
    thresholds = config.get("thresholds", {})
    red_threshold = float(thresholds.get("promo_readiness_red_threshold", 0.80))
    yellow_threshold = float(thresholds.get("promo_readiness_yellow_threshold", 0.95))

    logger.debug(
        "Promo readiness: vendor_id=%s promo_rows=%d po_rows=%d",
        vendor_id,
        len(promo_df.index),
        len(po_df.index),
    )

    if promo_df.empty:
        return {
            "overall_score": 1.0,
            "risk_tier": "green",
            "events": [],
        }

    promo = promo_df.copy()
    required = {"promo_id", "event_name", "start_date", "sku", "promoted_volume"}
    missing = required - set(promo.columns)
    if missing:
        raise ValueError(
            "promo_df is missing required columns: " + ", ".join(sorted(missing))
        )

    promo["_start"] = promo["start_date"].apply(_parse_date)
    if promo["_start"].isna().any():
        bad = promo.loc[promo["_start"].isna(), "promo_id"].tolist()
        raise ValueError(f"Invalid or missing start_date for promo_id(s): {bad}")

    promo["_vol"] = pd.to_numeric(promo["promoted_volume"], errors="coerce").fillna(0.0)

    event_scores: dict[str, dict[str, Any]] = {}
    event_vol_sums: dict[str, float] = {}
    event_meta: dict[str, tuple[str, str, date]] = {}

    for _, row in promo.iterrows():
        pid = str(row["promo_id"])
        sku = str(row["sku"])
        start = row["_start"]
        assert isinstance(start, date)
        vol = float(row["_vol"])

        if pid not in event_meta:
            event_meta[pid] = (
                str(row["event_name"]),
                pid,
                start,
            )

        po_qty = _po_qty_on_time_for_start(po_df, sku, start)
        if vol <= 0:
            line_score = 1.0
        else:
            line_score = min(1.0, po_qty / vol)

        if pid not in event_scores:
            event_scores[pid] = {"weighted": 0.0}
            event_vol_sums[pid] = 0.0

        event_scores[pid]["weighted"] += line_score * vol
        event_vol_sums[pid] += vol

    events_out: list[dict[str, Any]] = []
    overall_weighted = 0.0
    overall_vol = 0.0

    for pid in sorted(event_scores.keys()):
        name, _, first_start = event_meta[pid]
        total_v = event_vol_sums[pid]
        if total_v <= 0:
            ev_score = 1.0
        else:
            ev_score = event_scores[pid]["weighted"] / total_v
        covered = ev_score >= 1.0
        events_out.append(
            {
                "promo_id": pid,
                "event_name": name,
                "start_date": _format_date(first_start),
                "score": ev_score,
                "covered_by_po": covered,
            }
        )
        overall_weighted += ev_score * total_v
        overall_vol += total_v

    if overall_vol <= 0:
        overall_score = 1.0
    else:
        overall_score = overall_weighted / overall_vol

    tier = _risk_tier(overall_score, red_threshold, yellow_threshold)

    return {
        "overall_score": overall_score,
        "risk_tier": tier,
        "events": events_out,
    }
