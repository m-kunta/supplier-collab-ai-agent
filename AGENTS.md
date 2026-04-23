# AGENTS.md

**Author:** Mohith Kunta  
**GitHub:** [https://github.com/m-kunta](https://github.com/m-kunta)

This file provides guidance to AI coding agents (Claude, Codex, Gemini, etc.) when working with code in this repository.

---

## Commands

**Python environment** — the venv lives at `.venv/`. Always use it:
```bash
python3 -m venv .venv   # first time only
source .venv/bin/activate
pip install -r requirements.txt
```

**Run the CLI:**
```bash
python cli.py --vendor "Northstar Foods Co" --date "2026-04-03" --data-dir data/inbound/mock
python cli.py --help
```

**Run tests:**
```bash
pytest tests/ -v
```

**Run the HTTP API** (from repo root):
```bash
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

**Run the web UI**:
```bash
cd frontend
npm run dev   # UI only
```

**Run API + UI together**:
```bash
make dev
```

---

## Project Status

**Current phase:** Phase 7 — **Data Contracts + Production Landing Zone — In Progress.** Phases 1–6 are complete.

**Phase 6 (complete):** `generate_text_stream()` in `src/llm_providers.py` (Anthropic `messages.stream()`, single-chunk fallback for others). `summarize_request_stream()` in `src/agent.py` — compute engines → `engines` event → LLM token stream → persist → `done` event. `POST /api/briefings/stream` FastAPI SSE endpoint (async `asyncio.Queue` bridge). `createBriefingStreaming()` frontend client (`fetch()` + `ReadableStream`). `BriefingCreateForm` wired with live token preview pane, blinking cursor, auto-scroll, three-phase status labels.

**Phase 7 (in progress):** Pydantic-backed dataset schema validation in `src/data_validator.py` (schema model validation, row-model validation, numeric/date/nullability/enum checks, dataset-specific cross-field rules). Dataset validation gate in `src/agent.py` for both sync and streaming flows with required-vs-optional handling. Structured `validation_report` included in pipeline summaries and API responses. Persisted validation report artifact via `validation_report_path` in `output_files`. Production landing-zone scaffold now lives in `data/inbound/prod/` with a loadable manifest and header-only required CSV templates.

**Next work (remaining Phase 7 / Sprint 3):** Surface validation reporting in the frontend/history UI, continue error-handling hardening, and deepen production landing-zone support beyond the current scaffold/template.

**Reference:** `docs/implementation_plan.md`, `docs/supplier-collab-ai-scope-v1.0.md` section 13.

---

## Architecture

### What this project does

Pre-meeting intelligence agent for supplier collaboration. Ingests vendor performance CSV exports from a file-based landing zone, computes scorecard metrics and risk flags, then generates a synthesized briefing document via Claude for buyer/planner vendor meetings.

### Pipeline

```
cli.py / api → agent.py (orchestrator)
              │
    ┌─────────┼──────────────────────┐
    ▼         ▼                      ▼
Data Layer   Compute Layer          AI Layer
             │                       │
data_loader  scorecard_engine       llm_providers.py
data_validator  benchmark_engine       ↓
             po_risk_engine         Claude API
             oos_attribution        (narrative gen,
             promo_readiness         cross-domain synthesis,
                                     talking points)
              │
              ▼
         Output Layer
         output/ (md, future docx)
```

### Module responsibilities

| File | Role | Status |
|---|---|---|
| `cli.py` | CLI entry point. Parses `--vendor`, `--date`, `--data-dir`, `--lookback-weeks`, `--persona-emphasis`, `--include-benchmarks`, `--output-format`, `--category-filter`. | Working |
| `api/` | FastAPI: health, `POST /api/briefings` (blocking), **`POST /api/briefings/stream`** (true SSE via `asyncio.Queue`), list/get briefings, `GET /api/briefings/{id}/stream` (SSE replay), download, `GET /api/vendors`. | Working |
| `frontend/` | **[Phase 5–6 complete]** Next.js UI. App shell, history, briefing detail with SSE replay + tab dashboards. `BriefingCreateForm` wired to streaming endpoint with live token preview. | Working |
| `src/agent.py` | Full pipeline including LLM and markdown write; `summarize_request()` returns JSON for CLI and API. | Working |
| `src/config.py` | Loads `config/agent_config.yaml` with YAML parsing and validates that the top-level document is a mapping. Returns dict. | Working |
| `src/data_loader.py` | `resolve_data_dir()` and `load_manifest()` — reads `manifest.yaml` from the data landing zone with strict YAML mapping validation. | Working |
| `src/data_validator.py` | Manifest validation plus Pydantic-backed dataset contract validation: schema loading, row-model validation, type/nullability/enum/constraint checks, and dataset-specific rules. | Working |
| `src/scorecard_engine.py` | Scorecard metric computation: current value, 4w/13w trends, trend classification. | Working |
| `src/benchmark_engine.py` | Peer avg, BIC, gap-to-BIC, dollar-impact translation. | Working |
| `src/po_risk_engine.py` | PO risk tiering (red/yellow/green) based on days late vs. requested delivery date. Open/shipped assessed against the meeting date (`--date`); received POs assessed against actual receipt date when present. | Working |
| `src/oos_attribution.py` | OOS root-cause attribution: vendor-controllable vs. demand-driven, with PO cancellation cross-reference fallback for null cause codes. Returns counts, pct, units lost, recurring SKUs, top SKUs. | Working |
| `src/promo_readiness.py` | Promo readiness: on-time PO quantity vs. promoted volume per event; overall and per-event scores; red/yellow/green vs. config thresholds. | Working |
| `src/llm_providers.py` | Provider-agnostic LLM wrapper. `generate_text()` (blocking, retry) and `generate_text_stream()` (true Anthropic token streaming; single-chunk fallback for OpenAI/Google/Groq). All four providers wired. | All four live |

### Key implementation details

- **`.yaml` files now use real YAML parsing.** `src/config.py` and `src/data_loader.py` both use `yaml.safe_load()` and reject empty or non-mapping top-level documents with clear errors. Schema files under `data/schemas/` are also authored as native YAML.

- **Linkage computation is pre-computed, not in-context.** The design decision (scope doc §14) is that cross-domain analysis (PO×Promo, OOS attribution, benchmark gaps) is computed deterministically in the engine modules before being injected into the LLM prompt. Claude narrates; it doesn't compute. This keeps results reproducible and reduces token cost.

- **Graceful degradation pattern.** The agent generates the best briefing possible with available data. Three files are required (vendor_master, purchase_orders, vendor_performance); seven optional files enable additional sections. Missing optional files produce skip notes, not errors. See scope doc §7.3.

- **Vendor performance uses long/tall format.** `vendor_performance.csv` stores one row per vendor×metric×week. Adding a new metric means adding rows, not altering the schema. There are 15 metric codes across 4 tiers (Delivery & Fulfillment, Compliance & Quality, Commercial & Cost, Order Behavior).

- **Dual persona output.** The briefing is a single document with shared sections first (exec summary, scorecard, risk flags) followed by persona-specific deep-dives (§7 Buyer Focus, §8 Planner Focus). The `--persona-emphasis` flag controls which sections are expanded.

### Data contract

**Landing zone:** `data/inbound/{mock,prod}/`

Each landing zone contains:
- `manifest.yaml` — declares available files, freshness, row counts, environment
- CSV files per the 10-file schema inventory (3 required, 7 optional)

**Schemas:** `data/schemas/*.schema.yaml` — YAML schema definitions with `primary_key`, `required_columns`, `column_types`, nullability, enums, and constraints. Loaded and validated through Pydantic-backed schema models.

**Mock data:** Generated via `scripts/generate_mock_csvs.py` for 1 vendor (Northstar Foods Co) and 5 tables (13-week performance history, POs, OOS, Promo) seated in `data/inbound/mock/` to emulate pipeline injection.

**Production landing zone:** `data/inbound/prod/` is now a committed scaffold with `manifest.yaml` plus header-only required CSV templates (`vendor_master.csv`, `purchase_orders.csv`, `vendor_performance.csv`) so the app can target a production-formatted landing zone without storing real production data in git.

### Prompt versions

| File | Purpose |
|---|---|
| `prompts/briefing_v0.md` | MVP — Implemented. Mega-prompt forcing basic tone, quality, and 5 sections |
| `prompts/briefing_v1.md` | **Active (Phase 4).** Full 9-section prompt: exec summary, scorecard, benchmarks, PO risk, OOS attribution, promo readiness, §7 Buyer Focus, §8 Planner Focus, talking points. Dual-persona expansion. Uses all five engine outputs. |
| `prompts/briefing_v2.md` | Sprint 2 — cross-domain synthesis narrative refinements (reserved) |

Production prompts currently inject pre-computed structured data and request section-by-section narrative generation.

### Adding a new LLM provider (`src/llm_providers.py`)

1. Add an entry to `DEFAULT_MODELS` dict with the provider key and default model string.
2. Implement the actual API call inside `generate_text()` when moving past scaffold phase.
3. Provider is resolved from: config `default_provider` → `LLM_PROVIDER` env var → falls back to `anthropic`.

---

## Configuration

**`config/agent_config.yaml`** (YAML format):
- `defaults`: lookback_weeks, persona_emphasis, include_benchmarks, output_format, data_dir
- `llm`: default_provider, default_model, temperature
- `thresholds`: po_risk_days_late_red/yellow, po_open_statuses, promo_readiness_red/yellow_threshold

**Environment variables** (`.env.example` → `.env`):
- `LLM_PROVIDER` — overrides config default_provider
- `LLM_MODEL` — overrides config default_model
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY` — provider credentials

---

## Sprint Roadmap

| Sprint | Focus | Key Deliverable |
|---|---|---|
| **MVP** | Thin vertical slice | 1 vendor, 5 metrics, 5 sections, markdown output |
| **Sprint 1** | Full scorecard + benchmarking | 3 vendors, 14 metrics, BIC with $ impact, dual persona |
| **Sprint 2** | Cross-domain synthesis | PO×Promo linkage, OOS attribution, promo readiness |
| **Sprint 3** | Polished output + pipeline | DOCX output ✅, LLM orchestration, error handling |
| **Sprint 4** | Calendar integration + demo | Auto-trigger, leadership demo, pilot plan |
| **Phase 5** | Web Frontend ✅ | Next.js UI, FastAPI, SSE replay, engine dashboards, download, history |
| **Phase 6** | True LLM Streaming ✅ | `generate_text_stream()`, streaming orchestrator, `POST /api/briefings/stream`, live token preview |
| **Phase 7** | Data Contracts + Prod Landing Zone 🚧 | Pydantic validation, structured validation reports, persisted validation artifacts, prod landing-zone scaffold |

---

## Testing

Tests use `unittest` (not pytest fixtures). `tests/conftest.py` adds the project root to `sys.path`.

Current test coverage:
- Required scaffold paths exist
- CLI `--help` exposes all expected arguments
- Config loads with correct defaults and native YAML syntax
- Manifest path resolution works against mock data
- Provider selection resolves anthropic without a live API call
- Manifest/config edge-case handling and mock fixture integrity live in the Phase 1 foundation tests
- Scorecard engine: 17 tests covering current_value averaging, trend deltas, trend direction (consecutive-streak), lookback windowing, multiple metrics, and edge cases (`tests/test_scorecard_engine.py`)
- Benchmark engine: 15 tests covering peer avg, BIC percentile, gap-to-BIC, dollar impact, multiple metrics, input validation (missing columns, empty df, NaN rows) (`tests/test_benchmark_engine.py`)
- PO risk engine: 19 tests covering red/yellow/green tiering boundaries, received-PO lateness via actual_receipt_date, threshold configuration, mixed tiers, and graceful handling of missing columns/dates (`tests/test_po_risk_engine.py`)
- OOS attribution engine: 35 tests covering primary classification by root_cause_code, PO cancellation cross-reference fallback, bucket counts, vendor_controllable_pct, total_units_lost, recurring SKU detection, top SKU ranking, and edge cases (`tests/test_oos_attribution.py`)
- Promo readiness engine: 10 tests covering coverage tiers, cancelled/late PO handling, multi-SKU and multi-event weighting (`tests/test_promo_readiness.py`)
- Pipeline integration: `summarize_request` against mock landing zone with mocked LLM, plus dataset validation/reporting scenarios (`tests/test_p1_foundation.py`)
- FastAPI (`tests/test_api.py`): 13 tests — health, POST/GET briefings, list + limit pagination, 404s, SSE stream (content-type + sentinel), download 410 on missing file, `GET /api/vendors`, `llm_provider` override reflected in response, validation report presence.
- Streaming (Phase 6/7) — `tests/test_streaming.py`: 9 tests — Anthropic text-delta yielding, empty-chunk skipping, param pass-through, non-Anthropic fallback, orchestrator `engines`/`token`/`done` events, error event, pre-engine dataset-validation failure, SSE endpoint e2e, error forwarding.
- Output Renderer — `tests/test_output_renderer.py`: 5 tests — markdown front-matter, docx table generation and color mapping, `write_output` dispatcher logic, persisted validation report artifact.
- Frontend `createBriefingStreaming` — `frontend/lib/api.test.ts`: 4 tests — callback dispatch, error events, chunked SSE boundary handling, HTTP error rejection.
- Frontend `BriefingCreateForm` — `frontend/components/BriefingCreateForm.test.tsx`: 10 tests — payload shape, phase labels, live preview tokens, `onDone` navigation, `onError`, network retry.

Full backend suite: `.venv/bin/pytest tests/ -q` (**238 tests**). Frontend: `cd frontend && npm test` (**47 tests**). **Total: 285 tests, 0 failures.**

---

## Repository Naming

Local folder: `supplier_collab_ai_agent` (underscore, for workspace consistency).
GitHub remote: `supplier-collab-ai-agent` (hyphen).
