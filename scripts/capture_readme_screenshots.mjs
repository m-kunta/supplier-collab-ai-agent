import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("/Users/MKunta/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const FRONTEND_URL = "http://127.0.0.1:3000";
const SCREENSHOT_DIR = path.resolve("docs/images");

const briefingId = "demo-briefing-northstar";
const meetingDate = "2026-04-03";

const narrativeMarkdown = `# Northstar Foods Co Briefing

## Executive Summary
Northstar Foods Co enters this meeting with stable service momentum but rising execution risk around overdue inbound flow and weak forecast alignment on a handful of cereal SKUs. The strongest talking point is that supplier performance remains commercially manageable, but operational drift is starting to show up in areas that can affect promo readiness.

## AI-Synthesized Takeaways
- Fill rate remains above peer average, but the gap to best-in-class still represents recoverable sales.
- Three overdue ASN lines and multiple low-cover items point to near-term availability pressure.
- Forecast accuracy is improving overall, but underforecast concentration remains on a small cluster of high-value SKUs.

## Buyer Focus
Use the chargeback and trade-fund posture to frame a balanced commercial discussion: execution issues are visible, but so is room to protect margin through cleaner deductions and better funded activation.

## Planner Focus
Escalate ASN timing, low days-of-supply items, and the underforecast shortfall list first. Those are the most actionable levers before the next replenishment cycle.
`;

const streamingPreview = `# Northstar Foods Co Briefing

Executive summary is streaming live as the model turns scorecards, PO risk, OOS, promo readiness, and optional domain signals into a meeting-ready narrative.

- Benchmarks translated into talking points
- Deterministic engine output stitched into prose
- Buyer and planner views synthesized in one run`;

const briefingResponse = {
  id: briefingId,
  created_at: "2026-04-28T14:05:00Z",
  status: "completed",
  briefing_text: narrativeMarkdown,
  request: {
    vendor: "Northstar Foods Co",
    meeting_date: meetingDate,
    persona_emphasis: "both",
    output_format: "md",
  },
  validation_report: {
    is_valid: true,
    errors: [],
    warnings: ["Optional domains loaded with partial mock coverage for trade funds."],
  },
  scorecard: {
    fill_rate: {
      current_value: 0.964,
      trend_4w: 0.012,
      trend_13w: 0.019,
      trend_direction: "improving",
    },
    on_time_delivery: {
      current_value: 0.918,
      trend_4w: -0.008,
      trend_13w: 0.004,
      trend_direction: "declining",
    },
  },
  benchmarks: {
    fill_rate: {
      peer_avg: 0.952,
      best_in_class: 0.982,
      gap_to_bic: 0.018,
      dollar_impact: 185000,
    },
    on_time_delivery: {
      peer_avg: 0.924,
      best_in_class: 0.971,
      gap_to_bic: 0.053,
      dollar_impact: 97000,
    },
  },
  po_risk: {
    summary: { red: 2, yellow: 4, green: 18, total: 24 },
    line_items: [
      {
        po_number: "4500123011",
        po_line: 1,
        sku: "NS-CER-12",
        requested_delivery_date: "2026-04-01",
        po_status: "open",
        days_late: 4,
        risk_tier: "red",
      },
      {
        po_number: "4500123022",
        po_line: 2,
        sku: "NS-CER-48",
        requested_delivery_date: "2026-04-02",
        po_status: "open",
        days_late: 2,
        risk_tier: "yellow",
      },
    ],
  },
  oos_attribution: {
    total_oos_events: 12,
    vendor_controllable: 7,
    demand_driven: 3,
    unattributed: 2,
    vendor_controllable_pct: 0.58,
    total_units_lost: 1840,
    recurring_skus: ["NS-CER-12", "NS-CER-48"],
    top_skus: [
      { sku: "NS-CER-12", oos_count: 4, primary_cause: "Late PO", is_recurring: true },
      { sku: "NS-CER-48", oos_count: 3, primary_cause: "Forecast miss", is_recurring: true },
    ],
  },
  promo_readiness: {
    overall_score: 0.86,
    risk_tier: "yellow",
    events: [
      {
        promo_id: "PR-1042",
        event_name: "Back-to-School Cereal Feature",
        start_date: "2026-05-10",
        score: 0.82,
        covered_by_po: true,
      },
    ],
  },
  inventory_insights: {
    low_days_of_supply_sku_count: 5,
    promo_at_risk_count: 2,
    low_days_of_supply_skus: [
      { sku: "NS-CER-12", days_of_supply: 4.2 },
      { sku: "NS-CER-48", days_of_supply: 5.1 },
      { sku: "NS-GRN-06", days_of_supply: 5.7 },
    ],
  },
  forecast_insights: {
    avg_forecast_accuracy_pct: 0.88,
    underforecasted_week_count: 3,
    largest_underforecast_skus: [
      { sku: "NS-CER-48", shortfall_qty: 620 },
      { sku: "NS-CER-12", shortfall_qty: 410 },
    ],
  },
  asn_insights: {
    overdue_shipment_count: 3,
    on_time_receipt_pct: 0.91,
    top_overdue_asns: [
      { asn_number: "ASN-88431", days_overdue: 4 },
      { asn_number: "ASN-88444", days_overdue: 3 },
    ],
  },
  chargeback_insights: {
    total_chargeback_amount: 48250,
    open_chargeback_amount: 19750,
    top_chargeback_types: [
      { chargeback_type: "Labeling", count: 5, amount: 16400 },
      { chargeback_type: "Routing", count: 3, amount: 12250 },
    ],
  },
  trade_fund_insights: {
    spend_compliance_pct: 0.76,
    expiring_soon_count: 2,
    at_risk_funds: [
      { fund_id: "TF-2201", committed_amount: 40000, actual_spend: 23250 },
      { fund_id: "TF-2204", committed_amount: 25000, actual_spend: 12000 },
    ],
  },
};

const historyResponse = {
  briefings: [
    {
      id: briefingId,
      created_at: "2026-04-28T14:05:00Z",
      status: "completed",
      vendor_id: "V1001",
      vendor: "Northstar Foods Co",
      meeting_date: meetingDate,
      validation_report: {
        is_valid: true,
        errors: [],
        warnings: ["Optional domains partially populated."],
      },
    },
    {
      id: "demo-briefing-blueharbor",
      created_at: "2026-04-27T19:40:00Z",
      status: "completed",
      vendor_id: "V1002",
      vendor: "Blue Harbor Pantry",
      meeting_date: "2026-04-10",
      validation_report: {
        is_valid: false,
        errors: ["purchase_orders.csv row count mismatch vs manifest"],
        warnings: [],
      },
    },
    {
      id: "demo-briefing-cedarpeak",
      created_at: "2026-04-26T15:15:00Z",
      status: "completed",
      vendor_id: "V1003",
      vendor: "Cedar Peak Provisions",
      meeting_date: "2026-04-17",
      validation_report: {
        is_valid: true,
        errors: [],
        warnings: [],
      },
    },
  ],
  total: 3,
};

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function installCommonRoutes(page) {
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    });
  });

  await page.route("**/api/vendors*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        vendors: [
          {
            vendor_id: "V1001",
            vendor_name: "Northstar Foods Co",
            primary_category: "Cereal",
            buyer_name: "Alex Carter",
            planner_name: "Riley Brooks",
          },
          {
            vendor_id: "V1002",
            vendor_name: "Blue Harbor Pantry",
            primary_category: "Snacks",
            buyer_name: "Jordan Park",
            planner_name: "Morgan Lee",
          },
        ],
        total: 2,
        data_dir: "data/inbound/mock",
      }),
    });
  });
}

async function captureCreateStreaming(page) {
  await installCommonRoutes(page);
  await page.route("**/api/briefings/stream", async (route) => {
    const events = [
      `data: ${JSON.stringify({ type: "engines", engines: { scorecard: true, promo: true } })}\n\n`,
      `data: ${JSON.stringify({ type: "token", content: streamingPreview })}\n\n`,
    ].join("");

    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body: events,
    });
  });

  await page.goto(`${FRONTEND_URL}/briefings/new`, { waitUntil: "networkidle" });
  await page.getByLabel("Category Filter (optional)").fill("Cereal");
  await page.locator("#generate-briefing-btn").click();
  await page.getByText("Streaming briefing…").waitFor();
  await page.getByLabel("streaming preview").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, "ui-streaming-generation.png"),
    fullPage: true,
  });
}

async function captureNarrativeDetail(page) {
  await installCommonRoutes(page);
  await page.route(`**/api/briefings/${briefingId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(briefingResponse),
    });
  });

  await page.route(`**/api/briefings/${briefingId}/stream`, async (route) => {
    const events = [
      `data: ${JSON.stringify({ type: "token", content: narrativeMarkdown })}\n\n`,
      `data: ${JSON.stringify({ type: "done" })}\n\n`,
    ].join("");

    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body: events,
    });
  });

  await page.goto(`${FRONTEND_URL}/briefings/${briefingId}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Narrative" }).waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, "ui-briefing-detail-narrative.png"),
    fullPage: true,
  });
}

async function capturePhase8Detail(page) {
  await installCommonRoutes(page);
  await page.route(`**/api/briefings/${briefingId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(briefingResponse),
    });
  });

  await page.route(`**/api/briefings/${briefingId}/stream`, async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
      body: `data: ${JSON.stringify({ type: "done" })}\n\n`,
    });
  });

  await page.goto(`${FRONTEND_URL}/briefings/${briefingId}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Phase 8 Insights" }).click();
  await page.getByText("Supply-Side Insights").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, "ui-phase8-insights.png"),
    fullPage: true,
  });
}

async function captureHistory(page) {
  await installCommonRoutes(page);
  await page.route("**/api/briefings?limit=100", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(historyResponse),
    });
  });

  await page.goto(`${FRONTEND_URL}/briefings`, { waitUntil: "networkidle" });
  await page.getByText("Northstar Foods Co").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, "ui-briefing-history.png"),
    fullPage: true,
  });
}

async function main() {
  await ensureDir(SCREENSHOT_DIR);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1200 },
    colorScheme: "dark",
  });

  try {
    await captureCreateStreaming(page);
    await page.unrouteAll({ behavior: "ignoreErrors" });

    await captureNarrativeDetail(page);
    await page.unrouteAll({ behavior: "ignoreErrors" });

    await capturePhase8Detail(page);
    await page.unrouteAll({ behavior: "ignoreErrors" });

    await captureHistory(page);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
