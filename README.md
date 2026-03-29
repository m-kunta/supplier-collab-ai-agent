# Supplier Collaboration Briefing Agent (Supplier Collab AI)

![Status: In Progress](https://img.shields.io/badge/status-In_Progress-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Scope](https://img.shields.io/badge/scope-v1.0-brightgreen.svg)
![LLM](https://img.shields.io/badge/AI-Claude%20%7C%20OpenAI-purple.svg)

**Author:** Mohith Kunta  
**Project:** `supplier-collab-ai-agent`

## 🚀 High-Level Overview

The **Supplier Collaboration Briefing Agent** is an in-progress intelligence tool designed to automate pre-meeting preparation for category buyers and supply planners. Instead of requiring users to manually aggregate data across ERPs, WMS, and planning systems, this agent ingests exported vendor performance data (via standardized CSV files defined in a `manifest.yaml`) and synthesizes it into actionable, contextual briefing documents using an LLM.

*This repository is currently in an active developmental (scaffold) phase.*

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
- [ ] Implement `src/scorecard_engine.py` (calc 4-week, 13-week moving averages and trends).
- [ ] Implement `src/benchmark_engine.py` (determine category peer and gap-to-best-in-class metrics).
- [ ] Implement `src/po_risk_engine.py` (pipeline risk and late-PO classifications).
- [ ] Implement `src/promo_readiness.py` (promotional impacts and inventory supply cross-referencing).
- [ ] Implement `src/oos_attribution.py` (OOS event analysis and root-cause handling).

### Phase 4: AI Differentiation & Output Orchestration
- [ ] Finalize role-specific system prompts for Claude/OpenAI in `prompts/`.
- [ ] Integrate cross-domain analytical points into the generative prompt context.
- [ ] Orchestrate text generation pipeline inside `src/agent.py`.
- [ ] Render the LLM generated output to `md` output format.
- [ ] Render the LLM generated output to `docx` format.
- [ ] Hook up end-to-end integration test confirming `cli.py` prints the final briefing document.

## 🛠️ Planned Modules

- `cli.py`: Command-line entrypoint.
- `src/agent.py`: Orchestration entrypoint.
- `src/data_loader.py`: Manifest loader and dataset staging.
- `src/data_validator.py`: Schema and data quality checks logic.
- `src/scorecard_engine.py`: Scorecard metric shaping and analytics.
- `src/benchmark_engine.py`: Category peer and best-in-class calculations.
- `src/po_risk_engine.py`: Pipeline and late-PO risk classification pipeline.
- `src/oos_attribution.py`: OOS event analysis and root-cause handling.
- `src/promo_readiness.py`: Promotional metrics processing hooks.
- `src/llm_providers.py`: Model wrappers and agnostic text generation.

## 💻 Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python cli.py --help
pytest
```

## 🔍 Current CLI Shape

```bash
python cli.py --vendor "Kelloggs" --date "2026-04-03" --data-dir data/inbound/mock
```

*Note: The current CLI validates inputs, loads configuration parameters, resolves the data manifest, and prints a scaffold summary. Full document generation is unbuilt in the current sprint.*

## 📁 Repository Naming

The local project folder is named `supplier_collab_ai_agent` for workspace consistency.  
The GitHub repository name remains `supplier-collab-ai-agent`.
