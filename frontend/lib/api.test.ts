import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { createBriefing, listVendors } from "./api";

describe("frontend api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("listVendors sends data_dir query param and returns vendors", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          vendors: [{ vendor_id: "V1001", vendor_name: "Kelloggs" }],
          total: 1,
          data_dir: "/tmp/mock"
        }),
        { status: 200 }
      )
    );

    const payload = await listVendors("data/inbound/mock");

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(String(mockFetch.mock.calls[0][0])).toContain(
      "/api/vendors?data_dir=data%2Finbound%2Fmock"
    );
    expect(payload.total).toBe(1);
    expect(payload.vendors[0].vendor_id).toBe("V1001");
  });

  it("createBriefing posts JSON and returns id + status", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "123",
          created_at: "2026-04-13T00:00:00Z",
          status: "complete"
        }),
        { status: 200 }
      )
    );

    const payload = await createBriefing({
      vendor: "Kelloggs",
      meeting_date: "2026-04-03",
      data_dir: "data/inbound/mock",
      lookback_weeks: 13,
      persona_emphasis: "both",
      include_benchmarks: true,
      output_format: "md",
      category_filter: null
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(mockFetch.mock.calls[0][1]?.method).toBe("POST");
    expect(mockFetch.mock.calls[0][1]?.headers).toEqual({
      "Content-Type": "application/json"
    });
    expect(payload.id).toBe("123");
    expect(payload.status).toBe("complete");
  });
});
