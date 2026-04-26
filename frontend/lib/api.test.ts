import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  createBriefing,
  createBriefingStreaming,
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
          vendors: [{ vendor_id: "V1001", vendor_name: "Northstar Foods Co" }],
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
      vendor: "Northstar Foods Co",
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
              vendor: "Northstar Foods Co",
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
        vendor: "Northstar Foods Co",
        meeting_date: "2026-04-03",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null,
      })
    ).rejects.toThrowError("Failed to create briefing: bad request");
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

  // -------------------------------------------------------------------
  // Phase 6 — createBriefingStreaming
  // -------------------------------------------------------------------

  function sseBody(lines: string[]): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder();
    return new ReadableStream({
      start(controller) {
        for (const line of lines) controller.enqueue(encoder.encode(line));
        controller.close();
      }
    });
  }

  it("createBriefingStreaming dispatches engines/token/done callbacks", async () => {
    const mockFetch = vi.mocked(fetch);
    const body = sseBody([
      'data: {"type":"engines","engines":{"scorecard":{"OTIF":{"current_value":0.95}}}}\n\n',
      'data: {"type":"token","content":"Hello "}\n\n',
      'data: {"type":"token","content":"world"}\n\n',
      'data: {"type":"done","id":"brief-1","created_at":"2026-04-21T00:00:00Z","summary":{"id":"brief-1","created_at":"2026-04-21T00:00:00Z","status":"complete","briefing_text":"Hello world"}}\n\n'
    ]);
    mockFetch.mockResolvedValueOnce(
      new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } })
    );

    const onEngines = vi.fn();
    const onToken = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    await createBriefingStreaming(
      {
        vendor: "Acme Co",
        meeting_date: "2026-04-21",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null
      },
      { onEngines, onToken, onDone, onError }
    );

    expect(onEngines).toHaveBeenCalledOnce();
    expect(onEngines.mock.calls[0][0]).toHaveProperty("scorecard");
    expect(onToken).toHaveBeenCalledTimes(2);
    expect(onToken.mock.calls[0][0]).toBe("Hello ");
    expect(onToken.mock.calls[1][0]).toBe("world");
    expect(onDone).toHaveBeenCalledOnce();
    expect(onDone.mock.calls[0][0].id).toBe("brief-1");
    expect(onDone.mock.calls[0][0].briefing_text).toBe("Hello world");
    expect(onError).not.toHaveBeenCalled();
  });

  it("createBriefingStreaming dispatches error events", async () => {
    const mockFetch = vi.mocked(fetch);
    const body = sseBody(['data: {"type":"error","message":"boom"}\n\n']);
    mockFetch.mockResolvedValueOnce(
      new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } })
    );

    const onError = vi.fn();
    await createBriefingStreaming(
      {
        vendor: "Acme Co",
        meeting_date: "2026-04-21",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null
      },
      { onError }
    );
    expect(onError).toHaveBeenCalledWith("boom", undefined);
  });

  it("createBriefingStreaming handles chunked SSE with split event boundaries", async () => {
    const mockFetch = vi.mocked(fetch);
    // Split a single SSE event across multiple reader chunks.
    const body = sseBody([
      'data: {"type":"toke',
      'n","content":"chunk1"}\n\n',
      'data: {"type":"token","content":"chunk2"}\n\n'
    ]);
    mockFetch.mockResolvedValueOnce(
      new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } })
    );

    const onToken = vi.fn();
    await createBriefingStreaming(
      {
        vendor: "Acme Co",
        meeting_date: "2026-04-21",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null
      },
      { onToken }
    );
    expect(onToken).toHaveBeenCalledTimes(2);
    expect(onToken.mock.calls[0][0]).toBe("chunk1");
    expect(onToken.mock.calls[1][0]).toBe("chunk2");
  });

  it("createBriefingStreaming throws on HTTP error", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response("backend down", { status: 500 })
    );
    await expect(
      createBriefingStreaming({
        vendor: "Acme Co",
        meeting_date: "2026-04-21",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null
      })
    ).rejects.toThrow("backend down");
  });
});
