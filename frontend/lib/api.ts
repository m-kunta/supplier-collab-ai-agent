const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export interface BriefingResponse {
  id: string;
  created_at: string;
  status: string;
  [key: string]: unknown;
}

export async function listVendors(data_dir: string): Promise<VendorsResponse> {
  const url = new URL(`${API_BASE}/api/vendors`);
  url.searchParams.set("data_dir", data_dir);
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`Failed to list vendors: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<VendorsResponse>;
}

export async function createBriefing(
  payload: BriefingCreatePayload
): Promise<BriefingResponse> {
  const res = await fetch(`${API_BASE}/api/briefings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Failed to create briefing: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<BriefingResponse>;
}
