import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BriefingDetailPage from "./page";
import {
  getBriefing,
  getBriefingDownloadUrl,
  getBriefingStreamUrl
} from "../../../lib/api";

const closeMock = vi.fn();
let latestStream: MockEventSource | null = null;

class MockEventSource {
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  constructor(public readonly url: string) {
    latestStream = this;
  }
  close() {
    closeMock();
  }
}

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "brief-123" })
}));

vi.mock("../../../lib/api", () => ({
  getBriefing: vi.fn(),
  getBriefingDownloadUrl: vi.fn(() => "http://localhost:8000/api/briefings/brief-123/download"),
  getBriefingStreamUrl: vi.fn(() => "http://localhost:8000/api/briefings/brief-123/stream")
}));

describe("BriefingDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    latestStream = null;
    closeMock.mockClear();
    vi.stubGlobal("EventSource", MockEventSource);
    vi.mocked(getBriefing).mockResolvedValue({
      id: "brief-123",
      created_at: "2026-04-17T12:00:00Z",
      status: "complete",
      request: { vendor: "Kelloggs", meeting_date: "2026-04-03" },
      briefing_text: "Fallback text body"
    });
  });

  it("loads briefing metadata and fallback text", async () => {
    render(<BriefingDetailPage />);

    expect(await screen.findByText("ID: brief-123")).toBeInTheDocument();
    expect(screen.getByText("Vendor: Kelloggs")).toBeInTheDocument();
    expect(screen.getByText("Fallback text body")).toBeInTheDocument();
    expect(getBriefing).toHaveBeenCalledWith("brief-123");
    expect(getBriefingStreamUrl).toHaveBeenCalledWith("brief-123");
    expect(getBriefingDownloadUrl).toHaveBeenCalledWith("brief-123");
  });

  it("updates text from SSE token events", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    expect(latestStream).not.toBeNull();
    latestStream?.onmessage?.({
      data: JSON.stringify({ type: "token", content: "Live token" })
    } as MessageEvent);
    latestStream?.onmessage?.({
      data: JSON.stringify({ type: "done" })
    } as MessageEvent);

    await waitFor(() => {
      expect(screen.getByText("Live token")).toBeInTheDocument();
    });
    expect(screen.getByText("Stream Replay: Done")).toBeInTheDocument();
    expect(closeMock).toHaveBeenCalled();
  });
});
