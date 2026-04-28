# Supplier Collaboration Briefing Agent — Pilot Rollout Plan

## 1. Objective
Deploy the Briefing Agent to a targeted pilot group of Buyers and Supply Planners to measure time savings, negotiate better vendor outcomes, and refine the AI output before enterprise scale.

## 2. Pilot Scope
- **Duration:** 4 Weeks
- **Users:** 2 Category Buyers, 2 Supply Planners (Ideally working the same categories)
- **Vendors:** Top 20 strategic vendors within those categories.
- **Data Footprint:** Weekly extracts of the 3 required CSVs (Vendor Master, POs, Performance), plus 2 optional (OOS, Promo).

## 3. Phase 1: Data Onboarding (Weeks -2 to 0)
- **Data Engineering:** Set up automated or manual extracts from ERP/WMS to populate the `data/inbound/prod/` landing zone.
- **Validation:** Run the agent's Pydantic validator (`src/data_validator.py`) against the extracts to ensure schema compliance and fix any data type/nullability issues.
- **Dry Run:** Generate briefings for all 20 pilot vendors. Review manually to ensure hallucinations are zero and math (computed by the deterministic engines) is accurate.

## 4. Phase 2: User Enablement (Week 1)
- **Training Session (30 mins):** Walk users through the UI, explain how the AI synthesizes data (Deterministic Compute + AI Narrative), and set expectations.
- **Calendar Hookup (optional pilot extension):** Connect pilot calendars to the scheduler only if the team is also prepared to finish notification delivery. Otherwise, run the pilot with manual or UI-triggered briefing generation.
- **Feedback Loop Setup:** Create a dedicated Teams/Slack channel (`#pilot-supplier-agent`) for immediate feedback. 

## 5. Phase 3: Active Pilot (Weeks 2-4)
- **Usage:** Users rely on the auto-generated briefings for their scheduled weekly/monthly vendor syncs.
- **Prompt Refinement:** At the end of Week 2, review the generated talking points. Are they too aggressive? Too passive? Update `prompts/briefing_v1.md` based on user feedback.
- **Monitoring:** Monitor the FastAPI backend logs for any `AgentPipelineError` validation failures caused by shifting source data.

## 6. Success Metrics & ROI
To justify Phase 2 (Enterprise Rollout), we will measure:
1. **Time Saved:** Target: 30+ minutes saved per vendor meeting prep. (Measured via user survey).
2. **Adoption Rate:** Target: 80%+ of scheduled vendor meetings utilize the generated briefing document.
3. **Qualitative Outcomes:** Document at least 2 "wins" where the agent's cross-domain synthesis (e.g., catching a late PO threatening a promo) saved revenue or prevented a stockout.

## 7. Post-Pilot: Enterprise Scale
Upon successful pilot completion, the path to scale includes:
- Hooking up the remaining 5 optional data domains (Chargebacks, ASNs, etc.).
- Transitioning data ingestion from flat files to API/database direct connectors (if desired, though flat files scale fine).
- Completing delivery/notification workflows for scheduled briefings, then expanding calendar integration to support enterprise SSO (Microsoft Graph API).
