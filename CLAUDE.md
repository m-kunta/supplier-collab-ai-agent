# CLAUDE.md

**Author:** Mohith Kunta  
**GitHub:** [https://github.com/m-kunta](https://github.com/m-kunta)

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
Interactive docs: `http://127.0.0.1:8000/docs`

---

## Project Status

**Current phase:** Phase 6 — **True LLM Streaming — Complete.** All phases 1–6 are done.

**Phase 6 (complete):** `generate_text_stream()` added to `src/llm_providers.py` using the Anthropic SDK `messages.stream()` context manager for true token-level streaming. `summarize_request_stream()` added to `src/agent.py` — runs all compute engines, emits an `engines` event (full engine payload) so the UI can paint dashboards immediately, then streams LLM token chunks via `generate_text_stream()`, persists the briefing, and emits `done`. `POST /api/briefings/stream` FastAPI endpoint bridges the sync generator to an async `StreamingResponse` via `asyncio.Queue`. `createBriefingStreaming()` in `frontend/lib/api.ts` consumes the SSE stream via `fetch()` + `ReadableStream`. `BriefingCreateForm` is wired to the streaming endpoint with a live token preview pane (blinking cursor, auto-scroll), three-phase status labels, and navigates to the briefing detail page on `done`.

**Phase 5 (complete):** **FastAPI** in `api/` exposes: `GET /api/health`, `POST /api/briefings` (`llm_provider`/`llm_model` overrides), `GET /api/briefings` (history), `GET /api/briefings/{id}`, `GET /api/briefings/{id}/stream` (SSE replay of stored text in 25-char chunks), `GET /api/briefings/{id}/download` (`.md` attachment, 410 on missing file), `GET /api/vendors` (vendor list from landing zone). In-memory store (resets on restart). The **Next.js UI** (`frontend/`) includes the App Shell, Briefing History, Download, SSE replay with `react-markdown` + `remark-gfm`, and four engine dashboards (Scorecard, PO Risk, OOS, Promo Readiness) with tab navigation. A Dev Launcher (`scripts/dev.sh`, `Makefile`) starts API + UI with one command.

**Next work (Phase 7 / Sprint 3):** DOCX output format, Pydantic data contract validation, production data landing zone support.

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
| `src/agent.py` | Orchestrator. Loads config, manifest, validates, resolves vendor and LLM provider, loads vendor data, runs compute engines, prompt assembly, `generate_text()`, `write_output()`. `summarize_request()` returns JSON including `briefing_text`, `output_files`, `status`. | Working |
| `src/config.py` | Loads `config/agent_config.yaml` with YAML parsing and validates that the top-level document is a mapping. Returns dict. | Working |
| `src/data_loader.py` | `resolve_data_dir()` and `load_manifest()` — reads `manifest.yaml` from the data landing zone with strict YAML mapping validation. | Working |
| `src/data_validator.py` | `validate_manifest_shape()` — checks required top-level manifest keys. Will expand to full schema validation. | Minimal stub |
| `src/scorecard_engine.py` | Scorecard metric computation: current value, 4w/13w trends, trend classification. | Working |
| `src/benchmark_engine.py` | Peer avg, BIC, gap-to-BIC, dollar-impact translation. | Working |
| `src/po_risk_engine.py` | PO risk tiering (red/yellow/green) based on days late vs. requested delivery date. Open/shipped assessed against the meeting date (`--date`); received POs assessed against actual receipt date when present. | Working |
| `src/oos_attribution.py` | OOS root-cause attribution: vendor-controllable vs. demand-driven, with PO cancellation cross-reference fallback for null cause codes. Returns counts, pct, units lost, recurring SKUs, top SKUs. | Working |
| `src/promo_readiness.py` | Promo readiness: on-time PO quantity vs. promoted volume per event; overall and per-event scores; red/yellow/green vs. config thresholds. | Working |
| `src/llm_providers.py` | Provider-agnostic LLM wrapper. `resolve_provider()` returns a `ProviderSelection` dataclass. `generate_text()` (blocking, with exponential back-off retry) and `generate_text_stream()` (true token streaming via Anthropic `messages.stream()`; single-chunk fallback for OpenAI/Google/Groq). All four providers wired. | All four live |
| `src/prompt_builder.py` | `build_prompt(ctx)` — loads versioned prompt template from `prompts/`, serialises all engine outputs to JSON, substitutes `{{DATA_PAYLOAD}}`, `{{PERSONA_EMPHASIS}}`, `{{VENDOR_ID}}`, `{{MEETING_DATE}}`. | Working |
| `src/output_renderer.py` | `render_markdown(ctx)` — prepends YAML front-matter + appends footer. `write_output(ctx, output_dir, output_format)` — dispatches to md renderer and writes file. DOCX deferred to Sprint 3. | Markdown working; DOCX stub |
| `api/` | FastAPI app. `GET /api/health`, `POST /api/briefings` (blocking, thread-pool), **`POST /api/briefings/stream`** (true SSE streaming via `asyncio.Queue`), `GET /api/briefings`, `GET /api/briefings/{id}`, `GET /api/briefings/{id}/stream` (SSE replay), `GET /api/briefings/{id}/download`, `GET /api/vendors`. In-memory store. | Working |
| `frontend/` | **[Phase 5–6 — Complete]** Next.js web app. App shell, briefings history, briefing detail with SSE replay + tab dashboards (Scorecard, PO Risk, OOS, Promo). `BriefingCreateForm` wired to `POST /api/briefings/stream` with live token preview, blinking cursor, auto-scroll, and three-phase status labels. | Working |

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

**Schemas:** `data/schemas/*.schema.yaml` — YAML schema definitions with `primary_key`, `required_columns`, and `column_types`.

**Mock data:** Generated via `scripts/generate_mock_csvs.py` for 1 vendor (Northstar Foods Co) and 5 tables (13-week performance history, POs, OOS, Promo) seated in `data/inbound/mock/` to emulate pipeline injection.

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
- `thresholds`: po_risk_days_late_red/yellow, promo_readiness_red/yellow_threshold

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
| **Sprint 3** | Polished output + pipeline | DOCX output, LLM orchestration, error handling |
| **Sprint 4** | Calendar integration + demo | Auto-trigger, leadership demo, pilot plan |
| **Phase 5** | Web Frontend | Next.js UI, FastAPI, SSE replay, engine dashboards (Scorecard, PO Risk, OOS, Promo), download, history |
| **Phase 6** | True LLM Streaming ✅ | `generate_text_stream()`, streaming orchestrator, `POST /api/briefings/stream`, live token preview in `BriefingCreateForm` |

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
- PO risk engine: 19 tests covering red/yellow/green tiering, open vs. received PO date logic, config threshold overrides, multi-line aggregation, missing columns, and case-insensitive status handling (`tests/test_po_risk_engine.py`)
- OOS attribution engine: 35 tests covering primary classification by root_cause_code, PO cancellation cross-reference fallback, bucket counts, vendor_controllable_pct, total_units_lost, recurring SKU detection, top SKU ranking, and edge cases (`tests/test_oos_attribution.py`)
- Promo readiness engine: 10 tests covering coverage tiers, cancelled/late PO handling, multi-SKU and multi-event weighting (`tests/test_promo_readiness.py`)
- Pipeline integration: `summarize_request` against mock landing zone with mocked `generate_text` and `write_output` (`tests/test_p1_foundation.py`)
- LLM providers: 12 tests covering provider resolution, Anthropic happy path, retry logic on rate limits, and multi-provider paths (`tests/test_llm_providers.py`)
- FastAPI (`tests/test_api.py`): 13 tests — health, POST/GET briefings, list + limit pagination, 404s, SSE stream (content-type + sentinel), download 410 on missing file, `GET /api/vendors` (Northstar Foods Co present, bad-dir 404), `llm_provider` override reflected in response.
- Prompt builder: 12 tests covering template loading, variable substitution, JSON payload integrity, null optional data, and persona variants (`tests/test_prompt_builder.py`)
- Phase 4 E2E: 2 integration tests with mocked LLM call verifying `status=complete`, `briefing_text` populated, and `write_output` called correctly (`tests/test_p1_foundation.py`)

- Streaming (Phase 6): 8 backend tests (`tests/test_streaming.py`) — Anthropic text-delta yielding, empty-chunk skipping, param pass-through, non-Anthropic fallback, orchestrator `engines`/`token`/`done` events, error event, SSE endpoint e2e, error forwarding.
- Frontend `createBriefingStreaming`: 4 tests in `frontend/lib/api.test.ts` — callback dispatch, error events, chunked SSE boundary handling, HTTP error rejection.
- Frontend `BriefingCreateForm`: 10 tests in `frontend/components/BriefingCreateForm.test.tsx` — payload shape, phase labels, live preview tokens, `onDone` navigation, `onError`, network retry, generic exception.

Full backend suite: run `pytest tests/ -q` (**215 tests**). Frontend: `cd frontend && npm test` (**47 tests**). **Total: 262 tests, 0 failures.**

---

## Repository Naming

Local folder: `supplier_collab_ai_agent` (underscore, for workspace consistency).
GitHub remote: `supplier-collab-ai-agent` (hyphen).
