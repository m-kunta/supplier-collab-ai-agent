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
- Markdown write to `output/` (`src/output_renderer.py`). DOCX remains deferred.

### Phase 5 (in progress)

- **FastAPI (`api/`):** All REST endpoints complete — `GET /api/health`, `POST /api/briefings` (async, thread-pool executor, `llm_provider`/`llm_model` overrides, broad exception handling), `GET /api/briefings` (paginated list), `GET /api/briefings/{id}`, `GET /api/briefings/{id}/stream` (SSE replay), `GET /api/briefings/{id}/download` (FileResponse, 410 on missing file), `GET /api/vendors` (reads `vendor_master.csv` from any landing zone). CORS configurable via `CORS_ORIGINS` env var. In-memory `BriefingStore` (process-local).
- **Next:** Next.js frontend (`frontend/`) and combined dev launcher (`scripts/dev.sh`).
