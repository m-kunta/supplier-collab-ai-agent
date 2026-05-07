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

## Phase 9: Calendar & Notification Automation

1. **Calendar Ingestion Layer**
   - Create a service to parse upcoming meetings (e.g., via a mock JSON schedule or basic API integration like Google Calendar/Outlook).
   - Extract `vendor_id` and `meeting_date` from calendar invites to map to the correct data inputs.

2. **Automated Pipeline Triggering**
   - Implement a background scheduler (e.g., using `APScheduler` or a cron task in FastAPI) to automatically run the generation pipeline 24-48 hours before the scheduled meeting.

3. **Notification Delivery Workflows**
   - Build a new delivery module (`src/delivery.py`) to dispatch outputs.
   - **Chat Integration**: Add Slack/Teams webhooks to post a high-level summary and a direct link to the web UI dashboard.
   - **Email Integration**: Add SMTP or SendGrid/Mailgun capabilities to email the briefing with the rendered `.docx` output attached.

4. **Web UI Settings Dashboard**
   - Create a configuration page in the frontend to manage notification preferences.
   - Allow users to enable/disable automated triggers, set their webhook URLs, and configure target email addresses.

## Next Roadmap Items
- **Production Onboarding**: Add richer features for production onboarding of new suppliers or categories.
