import React from "react";
import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BriefingCreateForm } from "./BriefingCreateForm";
import { createBriefingStreaming, listVendors, startBackend } from "../lib/api";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("../lib/api", () => ({
  createBriefingStreaming: vi.fn(),
  listVendors: vi.fn(),
  startBackend: vi.fn(),
  checkHealth: vi.fn().mockResolvedValue(true),
}));

// Helper: build a createBriefingStreaming mock that calls the given sequence
// of callbacks then resolves.
function makeStreaming(
  sequence: ((cbs: Parameters<typeof createBriefingStreaming>[1]) => void)[]
) {
  return vi.fn(async (_payload: unknown, cbs: Parameters<typeof createBriefingStreaming>[1]) => {
    for (const step of sequence) step(cbs ?? {});
  });
}

describe("BriefingCreateForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listVendors).mockResolvedValue({
      vendors: [{ vendor_id: "V1001", vendor_name: "Northstar Foods Co" }],
      total: 1,
      data_dir: "data/inbound/mock",
    });
    vi.mocked(startBackend).mockResolvedValue({ ok: true });
  });

  it("loads vendors and renders form heading", async () => {
    vi.mocked(createBriefingStreaming).mockResolvedValue(undefined);

    render(
      <BriefingCreateForm
        heading="Generate Supplier Briefing"
        subheading="Run pipeline"
      />
    );

    expect(screen.getByText("Generate Supplier Briefing")).toBeInTheDocument();
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    expect(listVendors).toHaveBeenCalledWith("data/inbound/mock");
  });

  it("calls createBriefingStreaming with correct payload", async () => {
    vi.mocked(createBriefingStreaming).mockResolvedValue(undefined);

    render(
      <BriefingCreateForm heading="Generate" subheading="Run" />
    );

    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(createBriefingStreaming).toHaveBeenCalledOnce();
    });

    expect(createBriefingStreaming).toHaveBeenCalledWith(
      expect.objectContaining({
        vendor: "Northstar Foods Co",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null,
      }),
      expect.objectContaining({
        onEngines: expect.any(Function),
        onToken: expect.any(Function),
        onDone: expect.any(Function),
        onError: expect.any(Function),
      })
    );
  });

  it("shows 'Running compute engines' status while engines phase is active", async () => {
    // Never resolves during this test — just hangs after onEngines is never called
    vi.mocked(createBriefingStreaming).mockImplementation(
      () => new Promise(() => {}) // pending forever
    );

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(screen.getByText("Running compute engines…")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Generating…" })).toBeDisabled();
  });

  it("shows 'Streaming briefing' status when onEngines fires", async () => {
    vi.mocked(createBriefingStreaming).mockImplementation(
      async (_p, cbs) => {
        cbs?.onEngines?.({});
        await new Promise(() => {}); // keep streaming
      }
    );

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(screen.getByText("Streaming briefing…")).toBeInTheDocument();
    });
  });

  it("renders live preview tokens as they arrive", async () => {
    vi.mocked(createBriefingStreaming).mockImplementation(
      async (_p, cbs) => {
        cbs?.onEngines?.({});
        cbs?.onToken?.("Hello ");
        cbs?.onToken?.("world");
        await new Promise(() => {});
      }
    );

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(screen.getByLabelText("streaming preview")).toHaveTextContent("Hello world");
    });
  });

  it("navigates to briefing detail page on onDone", async () => {
    vi.mocked(createBriefingStreaming).mockImplementation(
      async (_p, cbs) => {
        cbs?.onEngines?.({});
        cbs?.onToken?.("Draft text");
        cbs?.onDone?.({
          id: "brief-stream-1",
          created_at: "2026-04-21T00:00:00Z",
          status: "complete",
          briefing_text: "Draft text",
        });
      }
    );

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/briefings/brief-stream-1");
    });
  });

  it("shows error message when onError fires", async () => {
    vi.mocked(createBriefingStreaming).mockImplementation(
      async (_p, cbs) => {
        cbs?.onError?.("LLM call failed");
      }
    );

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await screen.findByText("LLM call failed");
  });

  it("shows friendly message when API server is unreachable", async () => {
    vi.mocked(createBriefingStreaming).mockRejectedValue(new Error("Failed to fetch"));
    vi.mocked(startBackend).mockRejectedValue(new Error("start failed"));

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await screen.findByText(
      "Cannot reach the API server. Make sure the backend is running on port 8000."
    );
  });

  it("auto-starts backend and retries once on network failure", async () => {
    vi.mocked(createBriefingStreaming)
      .mockRejectedValueOnce(new Error("Failed to fetch"))
      .mockImplementationOnce(async (_p, cbs) => {
        cbs?.onEngines?.({});
        cbs?.onDone?.({
          id: "brief-retry-1",
          created_at: "2026-04-18T12:00:00Z",
          status: "complete",
        });
      });

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(startBackend).toHaveBeenCalledOnce();
      expect(createBriefingStreaming).toHaveBeenCalledTimes(2);
    });
    expect(pushMock).toHaveBeenCalledWith("/briefings/brief-retry-1");
  });

  it("shows generic error when non-network exception is thrown", async () => {
    vi.mocked(createBriefingStreaming).mockRejectedValue(new Error("Unexpected server error"));

    render(<BriefingCreateForm heading="Generate" subheading="Run" />);
    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await screen.findByText("Unexpected server error");
  });
});
