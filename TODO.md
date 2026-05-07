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

## Next Roadmap Items
- **Calendar & Notification Automation**: Deepen calendar work into delivery workflows (email/Teams/Slack or equivalent notification integrations) beyond simple scheduler polling.
- **Production Onboarding**: Add richer features for production onboarding of new suppliers or categories.
