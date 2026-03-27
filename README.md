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

### Phase 1: Foundation (Current)
- [x] Establish CLI contract and project scaffold.
- [x] Define data schemas and integration standards (see Scope & Data Integration Spec docs).
- [x] Build provider-agnostic LLM interface wrapper.
- [ ] Transition data loader to robust YAML parsing and a DataFrame engine (Pandas/Polars).

### Phase 2: Data Validation & Ingestion Layer
- [ ] Implement strong data contract validation via Pydantic.
- [ ] Build graceful degradation logic for missing optional domain files.
- [ ] Set up comprehensive logging framework for reporting missing schemas and mapping validation failures.

### Phase 3: Intelligence & Synthesis Pipelines
- [ ] Implement `scorecard_engine.py` resolving 4-week, 13-week moving averages and trends.
- [ ] Stitch cross-domain analysis points (e.g., PO × Promo Readiness, Safety Stock issues).
- [ ] Establish gap-to-best-in-class metrics within the benchmarking module.

### Phase 4: Output Rendering & Orchestration
- [ ] Finalize role-specific prompt engineering (Buyer and Planner focus modes).
- [ ] Output the final synthesized briefing agent document into Markdown and DOCX.

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
