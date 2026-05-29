# Supplier Collab AI Scaffold Plan

**Author:** Mohith Kunta ([@m-kunta](https://github.com/m-kunta))

## Summary

Add this plan as `docs/implementation_plan.md` inside the future project folder `/Users/MKunta/AGENTS/CODE/supplier_collab_ai_agent` once we switch out of Plan Mode. The first pass remains a **scaffold-only** build: set up the repo, package layout, config, docs, prompt placeholders, mock-data structure, and a provider-agnostic AI seam without implementing full briefing generation yet.

## Implementation Changes

- Create `/Users/MKunta/AGENTS/CODE/supplier_collab_ai_agent` and connect it to `https://github.com/m-kunta/supplier-collab-ai-agent`.
- Copy the scope document from `/Users/MKunta/AGENTS/CODE/Staging/supplier-collab-ai-agent-scope-v1.0.md` into `docs/scope_v1.0.md`.
- Add this plan file at `docs/implementation_plan.md`.
- Create the scaffold structure:
  - `README.md`, `.gitignore`, `.env.example`, `requirements.txt`
  - `cli.py`
  - `config/agent_config.yaml`
  - `data/inbound/mock/`, `data/inbound/prod/`, `data/schemas/`
  - `prompts/`
  - `src/`
  - `output/`, `docs/`, `tests/`
- Add importable placeholder modules in `src/`:
  - `agent.py`
  - `data_loader.py`
  - `data_validator.py`
  - `scorecard_engine.py`
  - `benchmark_engine.py`
  - `po_risk_engine.py`
  - `oos_attribution.py`
  - `promo_readiness.py`
  - `llm_providers.py`
- Use a provider-agnostic LLM wrapper with Claude as the default configured provider, but keep SDK usage isolated to `src/llm_providers.py`.
- Keep the initial interface CLI-first only with the scoped arguments defined in the scope doc.
- Seed placeholder manifest, schema, and prompt files for the required MVP domains.

## Public Interfaces / Types

- CLI:
  - `python cli.py --vendor <vendor> --date <YYYY-MM-DD> [options]`
- Config:
  - `config/agent_config.yaml` for defaults, thresholds, provider selection, and output settings
- LLM abstraction:
  - shared `generate_text(...)` style entrypoint in `src/llm_providers.py`
- Data contract placeholders:
  - manifest-driven landing zone under `data/inbound/`
  - schema YAML files under `data/schemas/`

## Test Plan

- Verify project imports cleanly.
- Verify `cli.py --help` exposes expected arguments.
- Verify config loading works.
- Verify mock manifest path resolution works.
- Verify provider selection logic can resolve the configured default without a live API call.
- Verify required scaffold directories and files exist.

## Assumptions

- Local folder name is `supplier_collab_ai_agent`.
- Remote GitHub repo remains `supplier-collab-ai-agent`.
- This phase does not include Streamlit, DOCX rendering, or full pipeline implementation.
- Python is the primary scaffold language; JS rendering pieces remain placeholders.

## Phase 3: Engine Layer (Partial — Scorecard + Benchmark)

Completed after scaffold. Implemented two compute engines with TDD.

### Scorecard Engine (`src/scorecard_engine.py`)

- `compute_scorecard(vendor_id, performance_df, lookback_weeks, config)` — computes per-metric scorecard.
- Returns dict keyed by metric_code with: `current_value` (4-week average), `trend_4w`, `trend_13w`, `trend_direction`.
- `trend_direction` uses a consecutive-streak check (configurable weeks + min_delta threshold) applied to the **most recent** N weekly deltas only.
- 17 tests in `tests/test_scorecard_engine.py`.

### Benchmark Engine (`src/benchmark_engine.py`)

- `compute_benchmarks(vendor_id, performance_df, config)` — computes per-metric peer benchmarks.
- Returns dict keyed by metric_code with: `peer_avg`, `best_in_class` (configurable percentile, default 90th), `gap_to_bic`, `dollar_impact` (None when no conversion factor configured).
- Uses latest-week-per-vendor to compute peer pool; target vendor excluded from peer set.
- 15 tests in `tests/test_benchmark_engine.py`.

### Additional Phase 3 Engines (completed after initial plan)

- `src/po_risk_engine.py` — `compute_po_risk` — ✅ (19 tests in `tests/test_po_risk_engine.py`)
- `src/oos_attribution.py` — `compute_oos_attribution` — ✅ (35 tests in `tests/test_oos_attribution.py`)
- `src/promo_readiness.py` — `compute_promo_readiness` — volume-weighted on-time PO coverage vs. `promoted_volume`, per-event and overall scores, red/yellow/green via `promo_readiness_red_threshold` / `promo_readiness_yellow_threshold` — ✅ (10 tests in `tests/test_promo_readiness.py`)

### Orchestration (`src/agent.py`)

- `run_pipeline()` executes, in order: load config → manifest → validate → resolve LLM provider → resolve vendor ID → `load_vendor_data` → `compute_scorecard` → `compute_benchmarks` (if `include_benchmarks`, using **full** `vendor_performance` for peer pool) → `compute_po_risk` (reference date = `--date`) → `compute_oos_attribution` (if `oos_events` loaded) → `compute_promo_readiness` (if `promo_calendar` loaded).
- `summarize_request()` returns JSON-serializable dict including engine outputs, `briefing_text`, `output_files`, `pipeline_notes`, and `status` (`"complete"` when the LLM step succeeds).

### Phase 4 (complete)

- Prompt assembly from `BriefingContext` / engine outputs (`src/prompt_builder.py`).
- `generate_text()` with provider SDKs and retries (`src/llm_providers.py`).
- Markdown and DOCX write to `output/` (`src/output_renderer.py`).

### Phase 5 (complete)

- **FastAPI (`api/`):** Core briefing REST endpoints complete — `GET /api/health`, `POST /api/briefings` (async, thread-pool executor, `llm_provider`/`llm_model` overrides, broad exception handling), `GET /api/briefings` (paginated list), `GET /api/briefings/{id}`, `GET /api/briefings/{id}/stream` (SSE replay), `GET /api/briefings/{id}/download` (FileResponse, 410 on missing file), `GET /api/vendors` (reads `vendor_master.csv` from any landing zone). CORS configurable via `CORS_ORIGINS` env var. In-memory `BriefingStore` (process-local).
- Next.js frontend dashboard/history/detail views are complete. Combined dev launcher is available via `make dev`; `frontend/npm run dev` runs UI-only.

### Phase 6 (complete)

- True provider streaming in `src/llm_providers.py` via `generate_text_stream()`.
- Streaming orchestrator in `src/agent.py` with `engines` → `token` → `done` event flow.
- `POST /api/briefings/stream` SSE endpoint in `api/main.py`.
- Frontend live-preview streaming flow via `createBriefingStreaming()` and `BriefingCreateForm`.

### Phase 7 (complete)

- Pydantic-backed schema contract validation in `src/data_validator.py`.
- Dataset validation stage in `src/agent.py` for sync and streaming paths with required-file failure and optional-file degradation.
- Structured `validation_report` added to briefing summaries and API responses.
- Validation report persisted as `validation_report_path` alongside rendered output artifacts.
- Frontend error hardening with `ValidationBanner` to display pipeline failure reports.
- Production data loader hardened against `EmptyDataError`, mixed types (via `low_memory=False`), and `utf-8-sig` encodings.
- Manifest `row_count` mismatch checking implemented.
- Production landing-zone scaffold at `data/inbound/prod/` fully operational.

### Phase 8 (complete)

- Optional domains are now **utilized** in deterministic backend engines and exposed in the briefing pipeline:
  - `inventory_position` → `src/inventory_insights.py`
  - `demand_forecast` → `src/forecast_insights.py`
  - `asn_receipts` → `src/asn_insights.py`
  - `chargebacks` → `src/chargeback_insights.py`
  - `trade_funds` → `src/trade_fund_insights.py`
- Prompt payload and briefing generation now incorporate all five optional domain outputs.
- Briefing detail UI now includes a consolidated `Phase 8 Insights` tab for these optional-domain summaries.
- Calendar polling / scheduled kickoff existed as a scaffold here; delivery notifications were completed in Phase 9.

### Phase 9 (complete)

- Calendar ingestion layer uses mock JSON schedule data from `data/calendar/meetings.json` with APScheduler-backed T-24h/T-2h briefing jobs in `src/scheduler.py`.
- Notification delivery in `src/delivery.py` dispatches Slack webhook, Teams webhook, and SMTP email notifications, with optional DOCX attachment support.
- File-backed notification settings live in `src/settings_store.py`, with FastAPI routes `GET /api/settings`, `PUT /api/settings`, and `GET /api/schedule`.
- Next.js `/settings` page lets users manage webhook URLs, SMTP config, automation toggle, and scheduled job status.
- Vendor onboarding scaffold includes `src/vendor_store.py`, `src/onboarding_packager.py`, `POST /api/vendors`, `GET /api/vendors/registered`, and `GET /api/vendors/{vendor_id}/onboarding-pack`.
- Vendor onboarding UI is complete at `frontend/app/vendors/page.tsx`: register vendors, view registered vendors, download per-vendor onboarding packs, and navigate via the Vendors header link.

### Phase 10 (in progress)

- Replace mock calendar ingestion with real Google Calendar / Outlook OAuth.
- Selectable JSON/SQLite persistence for notification settings and registered vendor onboarding records is implemented. Default remains JSON for compatibility; set `SUPPLIER_COLLAB_STORE_BACKEND=sqlite` and optionally `SUPPLIER_COLLAB_DB_PATH=config/supplier_collab.db` to use SQLite.
- Backend retry/dead-letter handling for scheduled notification delivery is implemented. `NotificationRetryService` retries channel sends, records attempts in SQLite `delivery_attempts`, and marks exhausted failures as `dead_letter`.
- Delivery-attempt visibility is implemented via `GET /api/deliveries` and the `/settings` page's recent delivery attempts panel.
- Expand supplier onboarding beyond the prototype UI into richer supplier/category workflows.

### Verification Snapshot

- Backend: `.venv/bin/pytest tests/ -q` → `343 passed`
- Vendor onboarding frontend slice: `cd frontend && npx vitest run --config vitest.config.ts app/vendors/page.test.tsx components/VendorRegisterForm.test.tsx lib/api.test.ts --no-cache` → `31 passed`
- Full frontend suite: `cd frontend && npm test -- --no-cache` → `92 passed`
