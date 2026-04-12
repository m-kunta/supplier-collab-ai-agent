# Supplier Collaboration Briefing Agent (Supplier Collab AI)

![Status: In Progress](https://img.shields.io/badge/status-In_Progress-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Scope](https://img.shields.io/badge/scope-v1.0-brightgreen.svg)
![LLM](https://img.shields.io/badge/AI-Claude%20%7C%20OpenAI-purple.svg)

**Author:** Mohith Kunta ([@m-kunta](https://github.com/m-kunta))  
**Project:** `supplier-collab-ai-agent`

## 🚀 High-Level Overview

The **Supplier Collaboration Briefing Agent** is an in-progress intelligence tool designed to automate pre-meeting preparation for category buyers and supply planners. Instead of requiring users to manually aggregate data across ERPs, WMS, and planning systems, this agent ingests exported vendor performance data (via standardized CSV files defined in a `manifest.yaml`) and synthesizes it into actionable, contextual briefing documents using an LLM.

*Current capabilities: the full pipeline (compute engines plus **LLM briefing** and **markdown** output to `output/`) runs from the CLI and from the **FastAPI** layer in `api/`. The API supports SSE streaming, `.md` downloads, vendor listing, and `llm_provider`/`llm_model` overrides. Phase 5 is adding a Next.js UI.*

## 📈 Development Plan & Roadmap

We are following a phased integration plan to move from structural scaffold to a full MVP.

### Phase 1: Foundation (Scaffold)
- [x] Establish CLI contract and project scaffold (`cli.py`, module structure).
- [x] Define data schemas and integration standards (Scope & Data Integration Spec).
- [x] Build provider-agnostic LLM interface wrapper (`src/llm_providers.py`).
- [x] Setup `README.md` and github repository (`supplier-collab-ai-agent`).
- [x] Transition `manifest.yaml` data loader to robust YAML parsing mechanism (e.g., `PyYAML`).
- [x] Harden manifest YAML loading by rejecting empty or non-mapping documents with clear errors, and add tests for native YAML plus invalid manifest shapes.
- [x] Establish foundational data manipulation engine (`pandas`) in requirements.

Phase 1 completion notes:
- Native YAML parsing is now used for `manifest.yaml`, `config/agent_config.yaml`, and `data/schemas/*.schema.yaml`.
- Foundation tests cover CLI contract, provider selection, YAML edge cases, and mock data/schema integrity.

### Phase 2: Data Validation & Ingestion Layer
- [ ] Implement `pydantic` models for strict data contract validation.
- [ ] Refactor `src/data_validator.py` to use Pydantic models for incoming CSV schema checks.
- [ ] Build graceful degradation logic for missing optional domain files.
- [ ] Set up a comprehensive Python logging framework (`logging`) replacing `print()` statements.
- [ ] Generate comprehensive Data Validation Reports via CLI output.

### Phase 3: Intelligence & Synthesis Pipelines (Engine Layer)
- [x] Implement `src/scorecard_engine.py` (calc 4-week, 13-week moving averages and trends).
- [x] Implement `src/benchmark_engine.py` (determine category peer and gap-to-best-in-class metrics).
- [x] Implement `src/po_risk_engine.py` (pipeline risk and late-PO classifications).
- [x] Implement `src/promo_readiness.py` (PO×promo coverage vs. promoted volume; red/yellow/green tier).
- [x] Implement `src/oos_attribution.py` (OOS event analysis and root-cause handling).
- [x] Wire all engines from `run_pipeline()` / `summarize_request()` with graceful skips for missing optional landing-zone files.

### Phase 4: AI Differentiation & Output Orchestration ✅
- [x] Finalize role-specific system prompts for Claude/OpenAI in `prompts/` (`briefing_v1.md` — 9 sections, dual-persona).
- [x] Integrate cross-domain analytical points into the generative prompt context (inject engine outputs from `BriefingContext` via `src/prompt_builder.py`).
- [x] Call `generate_text()` in `src/llm_providers.py` and assemble the briefing narrative in `src/agent.py` (Anthropic SDK with exponential back-off retry).
- [x] Render the LLM generated output to `md` output format (`src/output_renderer.py` with YAML front-matter).
- [ ] Render the LLM generated output to `docx` format (Sprint 3).
- [x] Hook up end-to-end integration test confirming `cli.py` writes or prints the final briefing document.

### Phase 5: Web Frontend (In progress)
- [x] **FastAPI backend** (`api/`) — async `POST /api/briefings` (thread-pool, `llm_provider`/`llm_model` overrides); `GET /api/briefings` (paginated); `GET /api/briefings/{id}`; `GET /api/health`; in-memory store.
- [x] **FastAPI** — SSE streaming (`GET /api/briefings/{id}/stream`), file download (`GET /api/briefings/{id}/download`), `GET /api/vendors`.
- [ ] **Next.js frontend** (`frontend/`) — premium dark-mode web UI with vendor selector, briefing form, live LLM streaming, and engine data dashboards (Scorecard, PO Pipeline, OOS, Promo Readiness).
- [ ] **Dev launcher** (`scripts/dev.sh`, `Makefile`) — single command starts both API and UI.
- [ ] **Streaming LLM output** — browser receives tokens in real-time via Server-Sent Events.
- [ ] **Download & history (UI)** — `.md` download button wired to download endpoint; history page consuming list API.

## 🛠️ Key modules

- `cli.py`: Command-line entrypoint.
- `api/`: FastAPI app (`uvicorn api.main:app`).
- `src/agent.py`: Orchestration entrypoint.
- `src/data_loader.py`: Manifest loader and dataset staging.
- `src/data_validator.py`: Schema and data quality checks logic.
- `src/scorecard_engine.py`: Scorecard metric shaping and analytics.
- `src/benchmark_engine.py`: Category peer and best-in-class calculations.
- `src/po_risk_engine.py`: Pipeline and late-PO risk classification pipeline.
- `src/oos_attribution.py`: OOS event analysis and root-cause handling.
- `src/promo_readiness.py`: Promo readiness scoring (on-time PO coverage vs. promoted volume).
- `src/llm_providers.py`: Model wrappers and agnostic text generation.

## 💻 Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python cli.py --help
pytest
# Optional — HTTP API (from repo root)
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## 🔍 Current CLI Shape

```bash
python cli.py --vendor "Kelloggs" --date "2026-04-03" --data-dir data/inbound/mock
```

*Note: The CLI prints JSON including engine outputs and, when the LLM step succeeds, `briefing_text`, `status: "complete"`, and `output_files` (paths written under `output/`). The same payload shape is returned by `POST /api/briefings` with additional `id` and `created_at` fields.*

## 📁 Repository Naming

The local project folder is named `supplier_collab_ai_agent` for workspace consistency.  
The GitHub repository name remains `supplier-collab-ai-agent`.
