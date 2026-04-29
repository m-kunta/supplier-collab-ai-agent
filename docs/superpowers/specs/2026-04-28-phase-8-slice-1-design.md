# Phase 8 Slice 1 Design

## Summary

Implement the first Phase 8 slice by wiring `inventory_position.csv` and
`demand_forecast.csv` into deterministic compute modules, then exposing their
outputs through the existing briefing pipeline and prompt payload.

This slice stays aligned with the repository's architecture: engine modules
compute reproducible facts, while the LLM narrates those facts in the briefing.

## Goals

- Add vendor-level inventory context that highlights low-cover risk and promo
  exposure.
- Add vendor-level forecast context that highlights demand accuracy and bias.
- Surface both datasets in pipeline summaries, streaming payloads, and prompt
  assembly.
- Preserve graceful degradation when either optional dataset is missing.

## Non-Goals

- No schema changes.
- No frontend-specific Phase 8 UI work beyond what already consumes the API
  payload.
- No attempt to fully rewrite `oos_attribution` or `promo_readiness` in this
  slice.
- No implementation yet for `asn_receipts`, `chargebacks`, or `trade_funds`.

## Approach Options

### Option 1: New Dedicated Insight Engines

Add `src/inventory_insights.py` and `src/forecast_insights.py`, wire them into
`BriefingContext`, `run_pipeline()`, and prompt serialization.

Pros:
- Matches current architecture and testing style.
- Clear ownership and future expansion path.
- Keeps prompt payload explicit.

Cons:
- Slightly more code than patching existing engines.

### Option 2: Fold Logic into Existing Engines

Inject inventory logic into `promo_readiness` and forecast logic into
`oos_attribution`.

Pros:
- Fewer new files.

Cons:
- Blurs module boundaries.
- Harder to grow into later Phase 8 domains.

### Option 3: Prompt-Only Aggregation

Load raw aggregates and let the prompt rely on that context directly.

Pros:
- Fastest to ship.

Cons:
- Violates the repo's deterministic-compute design principle.
- Weaker tests and less reproducibility.

## Chosen Design

Use Option 1.

### Inventory Insights

New module: `src/inventory_insights.py`

Input:
- vendor-scoped `inventory_position`
- optional vendor-scoped `promo_calendar`
- meeting date

Output shape:
- `snapshot_date`
- `sku_count`
- `location_count`
- `total_on_hand_qty`
- `total_allocated_qty`
- `total_in_transit_qty`
- `total_on_order_qty`
- `low_days_of_supply_sku_count`
- `low_days_of_supply_skus`
- `promo_at_risk_count`
- `promo_at_risk_events`

Rules:
- Low days-of-supply means `days_of_supply < 7`.
- Only consider rows with parseable `days_of_supply`.
- `low_days_of_supply_skus` returns the lowest-cover SKUs, ordered ascending,
  capped to a short list for prompt readability.
- Promo-at-risk events come from `promo_calendar` rows whose
  `inventory_need_date` is on or after the meeting date and where linked SKU
  inventory has low days of supply or insufficient on-hand plus in-transit plus
  on-order quantity versus committed quantity.

Graceful degradation:
- Missing `promo_calendar` still returns the inventory summary, with promo risk
  fields set to zero/empty.

### Forecast Insights

New module: `src/forecast_insights.py`

Input:
- vendor-scoped `demand_forecast`
- meeting date

Output shape:
- `week_count`
- `sku_count`
- `location_count`
- `avg_forecast_accuracy_pct`
- `avg_forecast_bias`
- `underforecasted_week_count`
- `overforecasted_week_count`
- `promo_period_accuracy_pct`
- `non_promo_period_accuracy_pct`
- `largest_underforecast_skus`

Rules:
- Use only rows with parseable `week_ending`.
- Use rows with `week_ending <= meeting_date` for accuracy and bias rollups.
- If precomputed `forecast_accuracy_pct` or `forecast_bias` is missing, derive
  it from `forecast_qty` and `actual_qty` when possible.
- An underforecasted row has negative bias; an overforecasted row has positive
  bias.
- `largest_underforecast_skus` groups by SKU and ranks the largest cumulative
  demand shortfall where `actual_qty > forecast_qty`.

Graceful degradation:
- Empty or future-only data returns a valid summary with null aggregate metrics
  and empty lists.

## Pipeline Changes

- Extend `BriefingContext` with `inventory_insights` and `forecast_insights`.
- Add `_stage_compute_inventory_insights()` after promo readiness inputs are
  available.
- Add `_stage_compute_forecast_insights()` alongside the other optional-domain
  stages.
- Include both outputs in:
  - `prompt_builder._serialise_engine_outputs()`
  - `summarize_request()` response
  - streaming final payload serialization

## Prompt Changes

Update `prompts/briefing_v1.md` so the model explicitly incorporates:
- inventory low-cover and promo-risk context into risk framing
- forecast accuracy and bias context into OOS and demand-side framing

The prompt should continue to treat these as optional sections and degrade
gracefully when keys are `null`.

## Testing

Follow TDD:

1. Add unit tests for `inventory_insights`.
2. Add unit tests for `forecast_insights`.
3. Add prompt-builder tests asserting both keys are serialized.
4. Add pipeline/orchestration tests asserting new summary keys are present and
   degrade gracefully when datasets are absent.

## Risks

- Optional-domain mock data is limited, so some integration coverage may need
  synthetic DataFrames rather than existing landing-zone fixtures.
- Promo risk heuristics must stay lightweight to avoid inventing precision the
  source data does not support.

## Success Criteria

- Running the pipeline with these optional datasets produces deterministic
  inventory and forecast summaries in the output payload.
- Existing flows still pass when the optional files are absent.
- New and existing automated tests pass.
