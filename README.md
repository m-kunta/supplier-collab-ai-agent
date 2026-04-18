# Supplier Collaboration Briefing Agent (Supplier Collab AI)

![Status: In Progress](https://img.shields.io/badge/status-In_Progress-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Scope](https://img.shields.io/badge/scope-v1.0-brightgreen.svg)
![LLM](https://img.shields.io/badge/AI-Claude%20%7C%20OpenAI-purple.svg)

**Author:** Mohith Kunta  
**GitHub:** [https://github.com/m-kunta](https://github.com/m-kunta)  
**Project:** `supplier-collab-ai-agent`

## 🚀 High-Level Overview

The **Supplier Collaboration Briefing Agent** is an intelligence tool that automates pre-meeting preparation for category buyers and supply planners. It ingests exported vendor performance data (standardized CSV files declared in a `manifest.yaml`), runs a suite of deterministic compute engines, and synthesizes everything into a structured, role-specific briefing document via an LLM — in under 60 seconds instead of the 30–60 minutes of manual spreadsheet work the meeting would otherwise require.

*Current capabilities: the full pipeline (compute engines + LLM briefing + markdown output to `output/`) runs from the CLI and from a **FastAPI** layer in `api/`. The API supports SSE streaming, `.md` downloads, vendor listing, and `llm_provider`/`llm_model` overrides. Phase 5 is adding a Next.js UI.*

---

## 🎯 The Business Problem

### Problem Statement

**Retailers and distributors lose significant revenue every year** — not because of missing data, but because the right insights aren't synthesized at the right time. When a category buyer walks into a quarterly business review with a $50M supplier, they typically have:

- 15 minutes of prep time (on a good day)
- Fragmented data across 4-6 different systems
- No benchmark context (how does this vendor compare to peers?)
- No dollar-impact translation (what does a 3% fill-rate gap actually cost us?)

The result? **Billions in unnegotiated performance improvements go unclaimed**, supply disruptions that could have been prevented are discovered mid-call, and buyers/planners spend 30-60 minutes per meeting doing spreadsheet archaeology instead of strategic supplier management.

The root cause isn't data availability — the data already exists across ERPs, WMS systems, and performance databases. The gap is **contextual synthesis at the speed of the meeting cadence**.

### User-Facing Benefits

| Benefit | Before | After |
|---------|--------|-------|
| **Prep Time** | 30-60 min manual | 15 seconds |
| **Data Context** | 4-6 systems to check | Single briefing document |
| **Benchmarking** | Peer comparison requires manual spreadsheet work | Auto-computed vs. category avg + best-in-class |
| **Dollar Impact** | Abstract metrics | Gap translated to $ (lost sales, excess inventory) |
| **Consistency** | Varies by individual experience | Standardized output every time |
| **Coverage** | Only tier-1 vendors get thorough prep | All vendors can be briefed in seconds |

### Who this is for

Organizations that buy goods from external suppliers operate a continuous cadence of **supplier collaboration meetings** — weekly business reviews, quarterly commercial reviews, promo readiness calls, escalation meetings triggered by service failures. Two roles drive these meetings:

| Persona | Primary Responsibility | What they need walking into a meeting |
|---|---|---|
| **Category Buyer** | Negotiates commercial terms, drives category growth, manages compliance and cost performance | Service-level trends vs. contract targets, compliance penalty exposure, cost benchmarks vs. best-in-class peers, talking points for commercial leverage |
| **Supply Planner** | Owns replenishment, PO pipeline health, and on-shelf availability | Which POs are at risk of being late, open OOS events and their root causes, whether the supplier can cover upcoming promotional volume |

A mid-size retailer may have a single buyer or planner managing 50–200 supplier relationships simultaneously. At that scale, thorough manual preparation for every meeting is impossible.

### The status quo — and why it breaks

Before a supplier meeting today, a buyer or planner typically:

1. Pulls a service-level report from the ERP or WMS
2. Opens the PO tracking spreadsheet to find late or at-risk orders
3. Manually compares the vendor's fill rate to peer vendors or a category target
4. Checks a separate OOS log to see if there are open events and tries to remember the cause
5. Looks up the promo calendar and cross-references PO quantities against promotional volume commitments
6. Writes up talking points from memory

This process takes **30–60 minutes per meeting** and routinely gets skipped when calendars are full. When it does happen, the quality is inconsistent — dependent on the individual's experience, how recently they touched the account, and how much time they had. Meetings happen without full context, leading to:

- Missed negotiation leverage (the buyer doesn't know the vendor is 15% below best-in-class on fill rate)
- Reactive conversations (the planner didn't see the three late POs until the vendor mentioned them)
- Duplicated effort (the same data pulled again next week for the same vendor)
- Uneven coverage (tier-1 vendors get thorough prep; tier-3 vendors get none)

### What this agent does differently

The Supplier Collaboration Briefing Agent collapses that 30–60 minute manual process into a single command:

```bash
python cli.py --vendor "Northstar Foods Co" --date "2026-04-03"
```

It reads structured exports from the systems the organization already uses, computes every analytical dimension a buyer or planner would want, and produces a publication-ready briefing document — without requiring the user to touch a spreadsheet.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SUPPLIER COLLAB AI AGENT                                    │
│                         Pipeline Architecture                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────────┐
                                    │   CLI / API      │
                                    │   (user input)   │
                                    └────────┬─────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
            ┌───────▼────────┐       ┌───────▼────────┐       ┌───────▼────────┐
            │  Data Layer   │       │ Compute Layer  │       │    AI Layer    │
            │               │       │                │       │                │
            │ data_loader   │       │scorecard_engine│       │llm_providers   │
            │ data_validator       │benchmark_engine│       │                │
            │ manifest.yaml │       │po_risk_engine  │       │ Claude/OpenAI │
            │ CSV files    │       │oos_attribution │       │                │
            │               │       │promo_readiness │       │ prompts/      │
            └───────┬───────┘       └───────┬────────┘       └───────┬────────┘
                    │                        │                        │
                    │          ┌─────────────┼─────────────┐          │
                    │          │             │             │          │
                    │          ▼             ▼             ▼          │
                    │   ┌─────────────────────────────────────────┐   │
                    │   │            agent.py (orchestrator)       │   │
                    │   │   • chains data load → compute → render  │   │
                    │   │   • injects engine outputs into prompt   │   │
                    │   └─────────────────────┬───────────────────┘   │
                    │                          │                     │
                    │              ┌───────────┴───────────┐         │
                    │              │                       │         │
                    │              ▼                       ▼         │
                    │   ┌─────────────────┐   ┌────────────────────┐ │
                    │   │  Output Layer   │   │   FastAPI API      │ │
                    │   │                 │   │                    │ │
                    │   │ output/*.md     │   │ POST /api/briefings│ │
                    │   │ DOCX (future)   │   │ GET  /api/vendors  │ │
                    │   └─────────────────┘   │ SSE stream, .md    │ │
                    │                          │ download          │ │
                    │                          └────────────────────┘ │
                    │                                                     │
                    └─────────────────────────────────────────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │   Briefing Output   │
                                    │                      │
                                    │ • Exec Summary       │
                                    │ • Scorecard + Trends │
                                    │ • Benchmarks (BIC)   │
                                    │ • PO Risk (R/Y/G)    │
                                    │ • OOS Attribution    │
                                    │ • Promo Readiness   │
                                    │ • Buyer/Planner Focus│
                                    │ • Talking Points     │
                                    └───────────────────────┘
```

The briefing covers:

- **Executive summary** — one-paragraph narrative of the vendor's current standing
- **Scorecard** — current value, 4-week and 13-week trend, and trend direction for up to 15 performance metrics across Delivery & Fulfillment, Compliance & Quality, Commercial & Cost, and Order Behavior
- **Benchmark comparison** — where the vendor sits vs. peer category average and best-in-class, with dollar-impact translation for gaps
- **PO pipeline risk** — red/yellow/green tiering of open and in-transit orders, with days-late calculations and risk explanations
- **OOS attribution** — root-cause breakdown of out-of-stock events (vendor-controllable vs. demand-driven), recurring SKUs, and units lost
- **Promo readiness** — on-time PO coverage vs. promoted volume per event, with readiness tiers (red/yellow/green)
- **Role-specific deep-dives** — §7 Buyer Focus (commercial, compliance, negotiation angles) and §8 Planner Focus (replenishment, supply continuity), expanded based on `--persona-emphasis`
- **Talking points** — LLM-generated, context-aware conversation starters for the meeting

---

## 📋 Use Cases

### 1. Weekly Supplier Business Review
A buyer prepares for a standing Monday meeting with a top-10 supplier. They run the agent on Friday; the briefing lands in `output/` with a complete narrative. On Monday they walk in knowing the vendor's fill rate has trended down 2.3 pp over 4 weeks, sits 8 pp below best-in-class, and that the gap translates to an estimated $420K in lost sales — before the vendor says a word.

### 2. OOS Escalation Meeting
A supply planner is pulled into an emergency call after a major SKU goes out of stock. They run the agent with the OOS events file loaded. The briefing identifies that 68% of OOS events this period are vendor-controllable (lead time failures), cross-references a cancelled PO that wasn't replaced, and surfaces the three SKUs with recurring OOS history. The planner arrives with evidence rather than anecdotes.

### 3. Promotional Readiness Review
Four weeks before a major promotional event, the buyer runs the agent with the promo calendar loaded. The briefing shows that PO coverage is at 72% of promoted volume for the hero SKU — flagged red — and that two supporting SKUs are yellow. They have four weeks to chase the supplier for confirmation or escalate with procurement. A problem that would have surfaced at 48 hours out is caught at 4 weeks.

### 4. Quarterly Commercial Review
A buyer preparing for a QBR runs the agent with benchmarks enabled. The briefing compares the vendor's cost index and compliance rate to category peers using the 90th-percentile best-in-class threshold, quantifies the gap in dollar terms, and generates talking points anchored in that data. The meeting shifts from a status update to a structured performance conversation.

---

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
- [x] **Dev launcher** (`scripts/dev.sh`, `Makefile`) — single command starts both API and UI.
- [x] **Streaming LLM output** — browser receives tokens in real-time via Server-Sent Events.
- [x] **Download & history (UI)** — `.md` download button wired to download endpoint; history page consuming list API.

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
cd frontend && npm install && cd ..
python cli.py --help
pytest
# Optional — HTTP API (from repo root)
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
# Optional — run API + UI together
make dev
# Optional — run UI only (API can be started from the header badge button)
cd frontend && npm run dev
```

## 🔍 Current CLI Shape

```bash
python cli.py --vendor "Northstar Foods Co" --date "2026-04-03" --data-dir data/inbound/mock
```

*Note: The CLI prints JSON including engine outputs and, when the LLM step succeeds, `briefing_text`, `status: "complete"`, and `output_files` (paths written under `output/`). The same payload shape is returned by `POST /api/briefings` with additional `id` and `created_at` fields.*

## 📁 Repository Naming

The local project folder is named `supplier_collab_ai_agent` for workspace consistency.  
The GitHub repository name remains `supplier-collab-ai-agent`.
