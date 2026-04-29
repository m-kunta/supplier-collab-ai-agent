# Phase 8 Narrative-Complete Design

## Summary

Complete the Phase 8 narrative slice by wiring the remaining optional domains
into deterministic engine modules:

- `asn_receipts`
- `chargebacks`
- `trade_funds`

This extends the first slice (`inventory_position` and `demand_forecast`) so
all five optional domains can contribute structured, testable facts to the
briefing narrative.

## Goals

- Add ASN and receipt quality context for planner-facing inbound reliability.
- Add chargeback cost and compliance context for buyer-facing negotiation and
  accountability framing.
- Add trade-fund execution context for buyer-facing promo and commercial
  discussions.
- Expose all three through the sync pipeline, streaming payload, and prompt
  serialization.

## Non-Goals

- No schema changes in this slice.
- No frontend-specific UI work beyond existing payload consumers.
- No deep refactor of PO risk, promo readiness, or output rendering.

## Design Constraint

Implementation will follow the repository's actual validated schemas rather
than the broader scope document examples when they differ. That means:

- `asn_receipts` uses fields like `expected_receipt_date`,
  `actual_receipt_date`, and `receipt_status`.
- `chargebacks` uses `issue_date`, `chargeback_amount`, and `dispute_status`.
- `trade_funds` uses `committed_amount`, `actual_spend`, `remaining_balance`,
  and optional `promo_id`.

This keeps the engine behavior aligned with the data contracts already enforced
by `src/data_validator.py`.

## Approach Options

### Option 1: New Dedicated Insight Engines

Add one focused engine per dataset and surface their outputs as first-class
payload fields.

Pros:
- Consistent with the architecture established by earlier engines.
- Clear ownership and clean unit-test seams.
- Easy to expand later without tangling responsibilities.

Cons:
- Slightly more code than inlining everything into existing modules.

### Option 2: Narrative-Only Enrichment Inside Existing Modules

Patch existing engine outputs with ASN/compliance/funding details and let the
prompt consume them indirectly.

Pros:
- Faster initial wiring.

Cons:
- Harder to test and reason about.
- Buries optional-domain logic inside unrelated modules.

## Chosen Design

Use Option 1.

## Engine Designs

### ASN Insights

New module: `src/asn_insights.py`

Inputs:
- vendor-scoped `asn_receipts`
- meeting date

Output shape:
- `shipment_count`
- `received_shipment_count`
- `overdue_shipment_count`
- `avg_receipt_lag_days`
- `on_time_receipt_pct`
- `fill_in_accuracy_pct`
- `top_overdue_asns`

Rules:
- Receipt lag is `actual_receipt_date - expected_receipt_date`.
- On-time means receipt lag `<= 0`.
- Overdue means no `actual_receipt_date` and `expected_receipt_date < meeting_date`,
  or explicit `receipt_status == "overdue"`.
- Fill-in accuracy compares `qty_received / qty_shipped` where both are present.
- `top_overdue_asns` ranks the most overdue open ASN lines by days overdue.

Graceful degradation:
- Empty input returns valid zero/null aggregates and empty lists.

### Chargeback Insights

New module: `src/chargeback_insights.py`

Inputs:
- vendor-scoped `chargebacks`
- meeting date

Output shape:
- `chargeback_count`
- `total_chargeback_amount`
- `open_chargeback_amount`
- `disputed_chargeback_amount`
- `most_recent_issue_date`
- `top_chargeback_types`
- `recent_open_chargebacks`

Rules:
- Open amount includes `dispute_status == "open"`.
- Disputed amount includes `dispute_status == "disputed"`.
- `top_chargeback_types` groups by type and summarizes count + dollars.
- `recent_open_chargebacks` returns the most recent unresolved items to support
  buyer narrative.

Graceful degradation:
- Empty input returns valid zero/null aggregates and empty lists.

### Trade Fund Insights

New module: `src/trade_fund_insights.py`

Inputs:
- vendor-scoped `trade_funds`
- optional vendor-scoped `promo_calendar`
- meeting date

Output shape:
- `fund_count`
- `total_committed_amount`
- `total_actual_spend`
- `total_remaining_balance`
- `spend_compliance_pct`
- `expiring_soon_count`
- `underutilized_fund_count`
- `promo_linked_fund_count`
- `at_risk_funds`

Rules:
- Spend compliance is `total_actual_spend / total_committed_amount` where
  committed total is positive.
- Expiring soon means `fund_period_end` within 30 days after the meeting date.
- Underutilized means an active or near-end fund has low spend versus committed.
  First-pass threshold: spend compliance below `0.5`.
- Promo-linked funds are funds with non-null `promo_id`.
- `at_risk_funds` surfaces soon-expiring and/or underutilized funds.

Graceful degradation:
- Empty input returns valid zero/null aggregates and empty lists.

## Pipeline Changes

- Extend `BriefingContext` with:
  - `asn_insights`
  - `chargeback_insights`
  - `trade_fund_insights`
- Add stage functions after the existing optional-domain stages.
- Include all three outputs in:
  - `prompt_builder._serialise_engine_outputs()`
  - `summarize_request()`
  - `_serialize_ctx_summary()`
  - streaming `engines` event payload

## Prompt Changes

Update `prompts/briefing_v1.md` so:
- ASN insights strengthen planner-facing inbound and receiving narrative.
- Chargeback insights strengthen buyer-facing compliance and deduction narrative.
- Trade-fund insights strengthen buyer-facing promo and commercial execution narrative.

The prompt must continue to degrade gracefully when any optional payload key is
`null`.

## Testing

TDD sequence:

1. Add unit tests for `asn_insights`.
2. Add unit tests for `chargeback_insights`.
3. Add unit tests for `trade_fund_insights`.
4. Extend prompt-builder, streaming, and sync-pipeline assertions for the new keys.
5. Run targeted tests, then full backend verification.

## Success Criteria

- All five optional domains now have deterministic backend outputs available to
  the briefing pipeline.
- Existing runs still succeed when optional files are absent.
- The prompt has structured facts for narrative-complete buyer/planner coverage.
- Backend tests pass with fresh verification.
