import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  createBriefing,
  getBriefing,
  getBriefingDownloadUrl,
  getBriefingStreamUrl,
  listBriefings,
  listVendors
} from "./api";

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

  it("listBriefings returns history rows with total", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          briefings: [
            {
              id: "b-1",
              created_at: "2026-04-13T00:00:00Z",
              status: "complete",
              vendor_id: "V1001",
              vendor: "Kelloggs",
              meeting_date: "2026-04-03"
            }
          ],
          total: 1
        }),
        { status: 200 }
      )
    );

    const payload = await listBriefings(20);

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(String(mockFetch.mock.calls[0][0])).toContain("/api/briefings?limit=20");
    expect(payload.total).toBe(1);
    expect(payload.briefings[0].id).toBe("b-1");
  });

  it("getBriefing fetches a single briefing by id", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "b-1",
          created_at: "2026-04-13T00:00:00Z",
          status: "complete",
          briefing_text: "# Briefing"
        }),
        { status: 200 }
      )
    );

    const payload = await getBriefing("b-1");

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(String(mockFetch.mock.calls[0][0])).toContain("/api/briefings/b-1");
    expect(payload.id).toBe("b-1");
  });

  it("builds stream and download urls", () => {
    expect(getBriefingStreamUrl("b-1")).toContain("/api/briefings/b-1/stream");
    expect(getBriefingDownloadUrl("b-1")).toContain("/api/briefings/b-1/download");
  });

  it("throws helpful error when createBriefing returns non-2xx", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "bad request" }), {
        status: 400,
        statusText: "Bad Request"
      })
    );

    await expect(
      createBriefing({
        vendor: "Kelloggs",
        meeting_date: "2026-04-03",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null
      })
    ).rejects.toThrow("Failed to create briefing: 400 Bad Request");
  });

  it("throws helpful error when listBriefings returns non-2xx", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response("server error", {
        status: 500,
        statusText: "Internal Server Error"
      })
    );

    await expect(listBriefings(10)).rejects.toThrow(
      "Failed to list briefings: 500 Internal Server Error"
    );
  });
});
