import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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
  getBriefingStreamUrl: vi.fn(() => "http://localhost:8000/api/briefings/brief-123/stream"),
  checkHealth: vi.fn().mockResolvedValue(true)
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
      request: { vendor: "Northstar Foods Co", meeting_date: "2026-04-03" },
      briefing_text: "Fallback text body"
    });
  });

  it("loads briefing metadata and fallback text", async () => {
    render(<BriefingDetailPage />);

    expect(await screen.findByText("ID: brief-123")).toBeInTheDocument();
    expect(screen.getByText("Vendor: Northstar Foods Co")).toBeInTheDocument();
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

  it("stream text overrides fallback text when both are present", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    latestStream?.onmessage?.({
      data: JSON.stringify({ type: "token", content: "Streamed content wins" })
    } as MessageEvent);

    await waitFor(() => {
      expect(screen.getByText("Streamed content wins")).toBeInTheDocument();
    });
    expect(screen.queryByText("Fallback text body")).not.toBeInTheDocument();
  });

  it("renders markdown headings as heading elements, not raw text", async () => {
    vi.mocked(getBriefing).mockResolvedValue({
      id: "brief-123",
      created_at: "2026-04-17T12:00:00Z",
      status: "complete",
      request: {},
      briefing_text: "## Section Header"
    });

    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    await waitFor(() => {
      const heading = screen.getByRole("heading", { level: 2, name: "Section Header" });
      expect(heading).toBeInTheDocument();
    });
  });

  it("renders markdown bold via remarkGfm as <strong>", async () => {
    vi.mocked(getBriefing).mockResolvedValue({
      id: "brief-123",
      created_at: "2026-04-17T12:00:00Z",
      status: "complete",
      request: {},
      briefing_text: "**important**"
    });

    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    await waitFor(() => {
      const bold = document.querySelector("strong");
      expect(bold).not.toBeNull();
      expect(bold?.textContent).toBe("important");
    });
  });

  it("renders GFM strikethrough as <del>", async () => {
    vi.mocked(getBriefing).mockResolvedValue({
      id: "brief-123",
      created_at: "2026-04-17T12:00:00Z",
      status: "complete",
      request: {},
      briefing_text: "~~deprecated~~"
    });

    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    await waitFor(() => {
      const del = document.querySelector("del");
      expect(del).not.toBeNull();
      expect(del?.textContent).toBe("deprecated");
    });
  });

  it("shows error message when getBriefing rejects", async () => {
    vi.mocked(getBriefing).mockRejectedValue(new Error("Not found"));

    render(<BriefingDetailPage />);

    expect(await screen.findByText("Not found")).toBeInTheDocument();
  });

  it("closes stream and marks done on SSE onerror", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    latestStream?.onerror?.(new Event("error"));

    await waitFor(() => {
      expect(screen.getByText("Stream Replay: Done")).toBeInTheDocument();
    });
    expect(closeMock).toHaveBeenCalled();
  });

  it("closes stream gracefully on malformed SSE JSON", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    latestStream?.onmessage?.({ data: "not-valid-json" } as MessageEvent);

    await waitFor(() => {
      expect(screen.getByText("Stream Replay: Done")).toBeInTheDocument();
    });
    expect(closeMock).toHaveBeenCalled();
  });

  it("shows fallback message when no briefing text is available", async () => {
    vi.mocked(getBriefing).mockResolvedValue({
      id: "brief-123",
      created_at: "2026-04-17T12:00:00Z",
      status: "complete",
      request: {},
      briefing_text: ""
    });

    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    await waitFor(() => {
      expect(screen.getByText("No briefing text available.")).toBeInTheDocument();
    });
  });

  it("renders all five tab buttons", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    expect(screen.getByRole("button", { name: "Narrative" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scorecard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "PO Risk" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OOS" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Promo" })).toBeInTheDocument();
  });

  it("narrative tab is active by default", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    expect(screen.getByText("Fallback text body")).toBeInTheDocument();
  });

  it("switching to Scorecard tab shows scorecard no-data when scorecard is absent", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    fireEvent.click(screen.getByRole("button", { name: "Scorecard" }));

    await waitFor(() => {
      expect(screen.getByText("No scorecard data available.")).toBeInTheDocument();
    });
    expect(screen.queryByText("Fallback text body")).not.toBeInTheDocument();
  });

  it("switching to PO Risk tab shows po-risk no-data when po_risk is absent", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    fireEvent.click(screen.getByRole("button", { name: "PO Risk" }));

    await waitFor(() => {
      expect(screen.getByText("No PO risk data available.")).toBeInTheDocument();
    });
  });

  it("switching to OOS tab shows oos no-data when oos_attribution is absent", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    fireEvent.click(screen.getByRole("button", { name: "OOS" }));

    await waitFor(() => {
      expect(screen.getByText("No OOS attribution data available.")).toBeInTheDocument();
    });
  });

  it("switching to Promo tab shows promo no-data when promo_readiness is absent", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("ID: brief-123");

    fireEvent.click(screen.getByRole("button", { name: "Promo" }));

    await waitFor(() => {
      expect(screen.getByText("No promo readiness data available.")).toBeInTheDocument();
    });
  });

  it("switching tabs hides narrative content", async () => {
    render(<BriefingDetailPage />);
    await screen.findByText("Fallback text body");

    fireEvent.click(screen.getByRole("button", { name: "Scorecard" }));

    await waitFor(() => {
      expect(screen.queryByText("Fallback text body")).not.toBeInTheDocument();
    });
  });
});
