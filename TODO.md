# Supplier Collab AI Agent — To-Dos

## Phase 8 Refinements

1. [x] **Frontend Polish (`Phase8InsightsPanel.tsx`)**
   - Improve the layout of the Phase 8 Insights panel.
   - Add better visual indicators (e.g., actual charts or progress graphs instead of plain tables).
   - Refine responsive design for different screen sizes.

2. [x] **Backend Engine Logic**
   - Enhance the insight engines (e.g., `src/inventory_insights.py`, `src/asn_insights.py`).
   - Generate more granular metrics or explore new data aggregations for optional domains.

3. [x] **LLM Prompt Integration**
   - Tweak `prompts/briefing_v1.md` to ensure the generated narratives make better use of the new Phase 8 insights.
   - Adjust how the LLM addresses specific issues like underforecasts, chargebacks, or at-risk trade funds based on the new data fields.

4. [x] **Data Degradation Handling**
   - Make the system handle missing Phase 8 data more robustly.
   - Add graceful degradation features both in the UI components and backend serialization logic when optional files aren't provided.

5. [x] **DOCX Output Formatting**
   - Address the TODO in `src/output_renderer.py` for passing explicit tier metadata alongside text for a more robust solution in DOCX table colour-coding (instead of relying on string-matching "red", "yellow", "green").

## Phase 9: Calendar & Notification Automation ✅ (prototype — complete 2026-05-08)

1. [x] **Calendar Ingestion Layer**
   - Mock JSON schedule (`data/calendar/meetings.json`) parsed by `src/scheduler.py`.
   - `vendor_id` and `meeting_date` extracted to map to the correct data inputs.

2. [x] **Automated Pipeline Triggering**
   - APScheduler polls calendar every 15 min; schedules T-24h and T-2h briefing jobs per meeting.

3. [x] **Notification Delivery Workflows**
   - `src/delivery.py`: `NotificationDispatcher` dispatches to Slack webhook, Teams webhook, and SMTP email.
   - Wired into scheduler post-briefing generation.

4. [x] **Web UI Settings Dashboard**
   - `frontend/app/settings/page.tsx`: manage webhook URLs, SMTP config, email recipients.
   - `GET /api/settings`, `PUT /api/settings`, `GET /api/schedule` FastAPI routes.
   - `src/settings_store.py`: file-backed JSON persistence (`config/notification_settings.json`).

## Next Roadmap Items
- **Phase 10 — Production Hardening**: Real Google Calendar / Outlook OAuth, DB-backed settings store, retry/dead-letter queue for notification delivery.
- **Production Onboarding**: Add richer features for production onboarding of new suppliers or categories.
