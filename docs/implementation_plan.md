# Supplier Collab AI Scaffold Plan

**Author:** Mohith Kunta ([@m-kunta](https://github.com/m-kunta))

## Summary

Add this plan as `docs/implementation_plan.md` inside the future project folder `/Users/MKunta/CODE/supplier_collab_ai_agent` once we switch out of Plan Mode. The first pass remains a **scaffold-only** build: set up the repo, package layout, config, docs, prompt placeholders, mock-data structure, and a provider-agnostic AI seam without implementing full briefing generation yet.

## Implementation Changes

- Create `/Users/MKunta/CODE/supplier_collab_ai_agent` and connect it to `https://github.com/m-kunta/supplier-collab-ai-agent`.
- Copy the scope document from `/Users/MKunta/CODE/Staging/supplier-collab-ai-agent-scope-v1.0.md` into `docs/scope_v1.0.md`.
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
