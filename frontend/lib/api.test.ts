import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  createBriefing,
  createBriefingStreaming,
  downloadOnboardingPack,
  getBriefing,
  getBriefingDownloadUrl,
  getBriefingStreamUrl,
  listRegisteredVendors,
  listBriefings,
  listVendors,
  registerVendor
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

  it("listRegisteredVendors returns registered vendors and total", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          vendors: [
            {
              id: "u1",
              vendor_id: "VEN001",
              vendor_name: "Northstar",
              category: "Grocery",
              tier: "Tier 1",
              status: "pending_data",
              created_at: "2026-05-11T00:00:00Z"
            }
          ],
          total: 1
        }),
        { status: 200 }
      )
    );

    const result = await listRegisteredVendors();

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(String(mockFetch.mock.calls[0][0])).toContain("/api/vendors/registered");
    expect(result.total).toBe(1);
    expect(result.vendors[0].vendor_id).toBe("VEN001");
  });

  it("registerVendor posts payload and returns saved record", async () => {
    const mockFetch = vi.mocked(fetch);
    const record = {
      id: "u1",
      vendor_id: "VEN002",
      vendor_name: "Apex",
      category: "Grocery",
      tier: "Tier 2",
      status: "pending_data",
      created_at: "2026-05-11T00:00:00Z"
    };
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(record), { status: 200 })
    );

    const result = await registerVendor({
      vendor_id: "VEN002",
      vendor_name: "Apex",
      category: "Grocery",
      tier: "Tier 2"
    });

    expect(result.vendor_id).toBe("VEN002");
    expect(mockFetch.mock.calls[0][1]?.method).toBe("POST");
    expect(mockFetch.mock.calls[0][1]?.headers).toEqual({
      "Content-Type": "application/json"
    });
    expect(mockFetch.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        vendor_id: "VEN002",
        vendor_name: "Apex",
        category: "Grocery",
        tier: "Tier 2"
      })
    );
  });

  it("registerVendor surfaces duplicate vendor errors with context", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Vendor already exists" }), {
        status: 409,
        statusText: "Conflict"
      })
    );

    await expect(
      registerVendor({
        vendor_id: "VEN002",
        vendor_name: "Apex",
        category: "Grocery",
        tier: "Tier 2"
      })
    ).rejects.toThrow("Failed to register vendor: Vendor already exists");
  });

  it("downloadOnboardingPack fetches zip and triggers download", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response(new Blob(["PK fake"], { type: "application/zip" }), {
        status: 200
      })
    );
    const createObjectURL = vi.fn(() => "blob:fake-url");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const clickMock = vi.fn();
    const createElementSpy = vi
      .spyOn(document, "createElement")
      .mockReturnValueOnce({
        href: "",
        download: "",
        click: clickMock
      } as unknown as HTMLAnchorElement);

    await downloadOnboardingPack("VEN001");

    expect(String(mockFetch.mock.calls[0][0])).toContain(
      "/api/vendors/VEN001/onboarding-pack"
    );
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(clickMock).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:fake-url");
    createElementSpy.mockRestore();
  });

  it("downloadOnboardingPack throws without creating a blob url on HTTP error", async () => {
    const mockFetch = vi.mocked(fetch);
    mockFetch.mockResolvedValueOnce(
      new Response("missing vendor", { status: 404 })
    );
    const createObjectURL = vi.fn();
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });

    await expect(downloadOnboardingPack("NOPE")).rejects.toThrow(
      "Failed to download onboarding pack: HTTP 404"
    );
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(revokeObjectURL).not.toHaveBeenCalled();
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

describe("getSettings", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it("returns parsed settings from /api/settings", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({
        slack_webhook_url: "https://hooks.slack.com/X",
        teams_webhook_url: "",
        email_enabled: false,
        email_smtp_host: "",
        email_smtp_port: 587,
        email_smtp_user: "",
        email_smtp_password: "",
        email_from: "",
        email_to: [],
      }), { status: 200 })
    );
    const { getSettings } = await import("./api");
    const settings = await getSettings();
    expect(settings.slack_webhook_url).toBe("https://hooks.slack.com/X");
  });
});

describe("updateSettings", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it("sends PUT with partial payload and returns updated settings", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ slack_webhook_url: "new-url", email_enabled: true }), { status: 200 })
    );
    const { updateSettings } = await import("./api");
    const result = await updateSettings({ slack_webhook_url: "new-url" });
    expect(result.slack_webhook_url).toBe("new-url");
    const [url, opts] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/api/settings");
    expect((opts as RequestInit).method).toBe("PUT");
  });
});

describe("getSchedule", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it("returns job list from /api/schedule", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ jobs: [{ id: "poll_calendar", name: "Poll", next_run: null }] }), { status: 200 })
    );
    const { getSchedule } = await import("./api");
    const schedule = await getSchedule();
    expect(schedule.jobs).toHaveLength(1);
    expect(schedule.jobs[0].id).toBe("poll_calendar");
  });
});
