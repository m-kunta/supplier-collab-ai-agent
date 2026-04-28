# Supplier Collaboration Briefing Agent — Leadership Demo Script

**Target Audience:** Supply Chain / Merchandising Executives, IT Leadership
**Goal:** Prove the value of moving from scattered dashboards to synthesized AI intelligence.
**Time Required:** ~10 minutes

## Pre-requisites
1. Have the application running (`make dev`).
2. Have the browser open to `http://localhost:3000`.
3. Have the IDE open to show the production data landing zone (`data/inbound/prod/`).

## Step 1: The "Before" State (The Scavenger Hunt)
*Script:* 
"Today, when our buyers prepare for a vendor meeting, they have to open five different systems. They pull a scorecard from SAP, check open POs in the WMS, look up promo calendars in a spreadsheet, and try to piece it all together. It takes 45 minutes, and they walk in with data, but no narrative."

*Action:* Show the raw CSV files in `data/inbound/prod/`.
*Script:* "This is what that data looks like. It's accurate, but it doesn't tell a story."

## Step 2: The "After" State (On-Demand Intelligence)
*Script:* "We built an AI Agent that acts as a Chief of Staff for every buyer. Let's ask it to prep for a meeting with Northstar Foods."

*Action:* Go to the web UI. Click "Create Briefing". Select "Northstar Foods Co", pick a date, and select "Both" for Persona Emphasis. Click Generate.
*Script:* "The agent isn't just making things up. It's querying our actual data contracts—computing 13-week trends, attributing out-of-stock root causes, and cross-referencing late POs against upcoming promos. Then, it uses Claude to synthesize the findings live."

## Step 3: Exploring the Output
*Script:* "In less than 15 seconds, we have a fully structured briefing."

*Action:* Scroll through the generated document.
* Highlight **Executive Summary**: "Notice how it immediately calls out the primary issue—fill rate drop."
* Highlight **OOS Impact**: "It doesn't just say 'we had out-of-stocks'. It attributes them to vendor-controllable root causes."
* Highlight **Promo Readiness**: "This is where the magic happens. It identified an upcoming promotion and cross-referenced it with an open PO that is currently running late, flagging a revenue risk before the meeting even starts."

## Step 4: Persona Targeting
*Script:* "Different people need different contexts. The agent tailors the deep dives."

*Action:* Show the Buyer vs. Planner sections.
*Script:* "The Buyer gets negotiation talking points and trade fund compliance. The Supply Planner gets lead time variability and safety stock impacts. Same data, different lenses."

## Step 5: The "Proactive" Future (Calendar Integration)
*Script:* "But we don't want buyers to even have to click 'Generate'. The agent is integrated into their calendar."

*Action:* Show the terminal logs where the `BriefingScheduler` is running.
*Script:* "The agent polls Google Calendar/Outlook. When it sees a vendor meeting tomorrow, it auto-triggers this exact pipeline and emails the briefing 24 hours in advance. No clicks required."

## The Close
*Script:* "This agent shifts our teams from data-gathering to decision-making, saving ~45 minutes per vendor meeting and driving more assertive, data-backed negotiations."
