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
  [key: string]: unknown;
}

export interface BriefingListItem {
  id: string;
  created_at: string;
  status: string;
  vendor_id?: string;
  vendor?: string;
  meeting_date?: string;
}

export interface BriefingListResponse {
  briefings: BriefingListItem[];
  total: number;
}

async function readJson<T>(res: Response, context: string): Promise<T> {
  if (!res.ok) {
    throw new Error(`${context}: ${res.status} ${res.statusText}`);
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
