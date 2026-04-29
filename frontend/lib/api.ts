const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export interface VendorRecord {
  vendor_id: string;
  vendor_name: string;
  [key: string]: unknown;
}

export interface VendorsResponse {
  vendors: VendorRecord[];
  total: number;
  data_dir: string;
}

export interface BriefingCreatePayload {
  vendor: string;
  meeting_date: string;
  data_dir: string;
  lookback_weeks: number;
  persona_emphasis: "buyer" | "planner" | "both";
  include_benchmarks: boolean;
  output_format: "md" | "docx" | "both";
  category_filter: string | null;
  llm_provider?: string | null;
  llm_model?: string | null;
}

export interface ScorecardMetric {
  current_value: number;
  trend_4w: number;
  trend_13w: number;
  trend_direction: "improving" | "declining" | "stable";
}

export interface BenchmarkMetric {
  peer_avg: number;
  best_in_class: number;
  gap_to_bic: number;
  dollar_impact: number | null;
}

export interface PoLineItem {
  po_number: string;
  po_line: number;
  sku: string;
  requested_delivery_date: string;
  po_status: string;
  days_late: number;
  risk_tier: "red" | "yellow" | "green";
}

export interface PoRiskData {
  summary: { red: number; yellow: number; green: number; total: number };
  line_items: PoLineItem[];
}

export interface OosTopSku {
  sku: string;
  oos_count: number;
  primary_cause: string;
  is_recurring: boolean;
}

export interface OosAttribution {
  total_oos_events: number;
  vendor_controllable: number;
  demand_driven: number;
  unattributed: number;
  vendor_controllable_pct: number;
  total_units_lost: number;
  recurring_skus: string[];
  top_skus: OosTopSku[];
}

export interface PromoEvent {
  promo_id: string;
  event_name: string;
  start_date: string;
  score: number;
  covered_by_po: boolean;
}

export interface PromoReadiness {
  overall_score: number;
  risk_tier: "red" | "yellow" | "green";
  events: PromoEvent[];
}

export interface InventoryInsightSku {
  sku: string;
  days_of_supply?: number;
  qty_on_hand?: number;
}

export interface InventoryInsights {
  low_days_of_supply_sku_count: number;
  promo_at_risk_count: number;
  low_days_of_supply_skus: InventoryInsightSku[];
}

export interface ForecastUnderSku {
  sku: string;
  shortfall_qty: number;
}

export interface ForecastInsights {
  avg_forecast_accuracy_pct: number | null;
  underforecasted_week_count: number;
  largest_underforecast_skus: ForecastUnderSku[];
}

export interface AsnOverdue {
  asn_number: string;
  days_overdue: number;
}

export interface AsnInsights {
  overdue_shipment_count: number;
  on_time_receipt_pct: number | null;
  top_overdue_asns: AsnOverdue[];
}

export interface ChargebackTypeSummary {
  chargeback_type: string;
  count: number;
  amount: number;
}

export interface ChargebackInsights {
  total_chargeback_amount: number;
  open_chargeback_amount: number;
  top_chargeback_types: ChargebackTypeSummary[];
}

export interface AtRiskFund {
  fund_id: string;
  committed_amount: number;
  actual_spend: number;
}

export interface TradeFundInsights {
  spend_compliance_pct: number | null;
  expiring_soon_count: number;
  at_risk_funds: AtRiskFund[];
}

export interface ValidationReport {
  errors: string[];
  warnings: string[];
  is_valid: boolean;
}

export interface BriefingResponse {
  id: string;
  created_at: string;
  status: string;
  briefing_text?: string;
  request?: unknown;
  vendor_id?: string;
  scorecard?: Record<string, ScorecardMetric>;
  benchmarks?: Record<string, BenchmarkMetric>;
  po_risk?: PoRiskData;
  oos_attribution?: OosAttribution;
  promo_readiness?: PromoReadiness;
  inventory_insights?: InventoryInsights;
  forecast_insights?: ForecastInsights;
  asn_insights?: AsnInsights;
  chargeback_insights?: ChargebackInsights;
  trade_fund_insights?: TradeFundInsights;
  validation_report?: ValidationReport;
  [key: string]: unknown;
}

export interface BriefingListItem {
  id: string;
  created_at: string;
  status: string;
  vendor_id?: string;
  vendor?: string;
  meeting_date?: string;
  validation_report?: ValidationReport;
}

export interface BriefingListResponse {
  briefings: BriefingListItem[];
  total: number;
}

export class ApiError extends Error {
  public validation_report?: ValidationReport;
  constructor(message: string, validation_report?: ValidationReport) {
    super(message);
    this.name = "ApiError";
    this.validation_report = validation_report;
  }
}

async function readJson<T>(res: Response, context: string): Promise<T> {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    try {
      if (text) {
        const data = JSON.parse(text);
        if (data && data.detail) {
          if (typeof data.detail === "string") {
            throw new ApiError(`${context}: ${data.detail}`);
          } else if (data.detail.message) {
            throw new ApiError(`${context}: ${data.detail.message}`, data.detail.validation_report);
          }
        }
      }
    } catch (e) {
      if (e instanceof ApiError) throw e;
    }
    throw new ApiError(`${context}: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function listVendors(data_dir: string): Promise<VendorsResponse> {
  const url = new URL(`${API_BASE}/api/vendors`);
  url.searchParams.set("data_dir", data_dir);
  const res = await fetch(url.toString());
  return readJson<VendorsResponse>(res, "Failed to list vendors");
}

export async function createBriefing(
  payload: BriefingCreatePayload
): Promise<BriefingResponse> {
  const res = await fetch(`${API_BASE}/api/briefings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  return readJson<BriefingResponse>(res, "Failed to create briefing");
}

/**
 * Phase 6 — event types emitted by `POST /api/briefings/stream`.
 */
export type StreamEvent =
  | { type: "engines"; engines: Record<string, unknown> }
  | { type: "token"; content: string }
  | {
      type: "done";
      id: string;
      created_at: string;
      summary: BriefingResponse;
    }
  | { type: "error"; message: string; validation_report?: ValidationReport };

export interface StreamCallbacks {
  onEngines?: (engines: Record<string, unknown>) => void;
  onToken?: (chunk: string) => void;
  onDone?: (briefing: BriefingResponse & { id: string; created_at: string }) => void;
  onError?: (message: string, validation_report?: ValidationReport) => void;
}

/**
 * POST `/api/briefings/stream` and dispatch SSE events via callbacks.
 *
 * Uses `fetch()` + a ReadableStream reader (EventSource is GET-only).
 * Rejects only on network/HTTP failures; LLM-level errors arrive via `onError`.
 */
export async function createBriefingStreaming(
  payload: BriefingCreatePayload,
  callbacks: StreamCallbacks = {}
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/briefings/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(payload)
  });

  if (!res.ok || !res.body) {
    let errMessage = `Stream request failed (${res.status})`;
    let errReport: ValidationReport | undefined;
    const text = await res.text().catch(() => "");
    if (text) errMessage = text;
    
    try {
      if (text) {
        const data = JSON.parse(text);
        if (data && data.detail) {
          if (typeof data.detail === "string") {
            errMessage = data.detail;
          } else if (data.detail.message) {
            errMessage = data.detail.message;
            errReport = data.detail.validation_report;
          }
        }
      }
    } catch {
      // not json, keep text
    }
    
    // We can call onError directly here to surface the validation report
    // if the initial connection fails with a 400.
    if (errReport && callbacks.onError) {
      callbacks.onError(errMessage, errReport);
      throw new Error("API_ERROR_HANDLED"); // Dummy error to halt execution without unhandled rejections
    }
    throw new Error(errMessage);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (rawLine: string): void => {
    if (!rawLine.startsWith("data: ")) return;
    const payload = rawLine.slice("data: ".length);
    let evt: StreamEvent;
    try {
      evt = JSON.parse(payload) as StreamEvent;
    } catch {
      return;
    }
    switch (evt.type) {
      case "engines":
        callbacks.onEngines?.(evt.engines);
        break;
      case "token":
        callbacks.onToken?.(evt.content);
        break;
      case "done":
        callbacks.onDone?.({ ...evt.summary, id: evt.id, created_at: evt.created_at });
        break;
      case "error":
        callbacks.onError?.(evt.message, evt.validation_report);
        break;
    }
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE events are separated by a blank line (\n\n). Dispatch complete ones.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const chunk = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of chunk.split("\n")) dispatch(line);
    }
  }
  // Flush any trailing event (no closing blank line).
  if (buffer.trim()) {
    for (const line of buffer.split("\n")) dispatch(line);
  }
}

export async function startBackend(): Promise<{ ok: boolean; error?: string }> {
  const res = await fetch("/api/start-backend", {
    method: "POST",
    cache: "no-store"
  });
  return readJson<{ ok: boolean; error?: string }>(res, "Failed to start backend");
}

export async function listBriefings(limit = 50): Promise<BriefingListResponse> {
  const url = new URL(`${API_BASE}/api/briefings`);
  url.searchParams.set("limit", String(limit));
  const res = await fetch(url.toString());
  return readJson<BriefingListResponse>(res, "Failed to list briefings");
}

export async function getBriefing(briefingId: string): Promise<BriefingResponse> {
  const res = await fetch(`${API_BASE}/api/briefings/${briefingId}`);
  return readJson<BriefingResponse>(res, "Failed to load briefing");
}

export function getBriefingStreamUrl(briefingId: string): string {
  return `${API_BASE}/api/briefings/${briefingId}/stream`;
}

export function getBriefingDownloadUrl(briefingId: string): string {
  return `${API_BASE}/api/briefings/${briefingId}/download`;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      signal: AbortSignal.timeout(2000),
      cache: "no-store"
    });
    return res.ok;
  } catch {
    return false;
  }
}
