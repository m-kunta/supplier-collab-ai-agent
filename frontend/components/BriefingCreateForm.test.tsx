import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BriefingCreateForm } from "./BriefingCreateForm";
import { createBriefing, listVendors, startBackend } from "../lib/api";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock })
}));

vi.mock("../lib/api", () => ({
  createBriefing: vi.fn(),
  listVendors: vi.fn(),
  startBackend: vi.fn(),
  checkHealth: vi.fn().mockResolvedValue(true)
}));

describe("BriefingCreateForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listVendors).mockResolvedValue({
      vendors: [{ vendor_id: "V1001", vendor_name: "Northstar Foods Co" }],
      total: 1,
      data_dir: "data/inbound/mock"
    });
    vi.mocked(startBackend).mockResolvedValue({ ok: true });
  });

  it("loads vendors and renders form heading", async () => {
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

  it("submits payload and routes to detail page", async () => {
    vi.mocked(createBriefing).mockResolvedValue({
      id: "brief-123",
      created_at: "2026-04-17T12:00:00Z",
      status: "complete"
    });

    render(
      <BriefingCreateForm
        heading="Generate Supplier Briefing"
        subheading="Run pipeline"
      />
    );

    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(
      screen.getByRole("button", { name: "Generate Briefing" })
    );

    await waitFor(() => {
      expect(createBriefing).toHaveBeenCalledOnce();
    });
    expect(createBriefing).toHaveBeenCalledWith(
      expect.objectContaining({
        vendor: "Northstar Foods Co",
        data_dir: "data/inbound/mock",
        lookback_weeks: 13,
        persona_emphasis: "both",
        include_benchmarks: true,
        output_format: "md",
        category_filter: null
      })
    );
    expect(pushMock).toHaveBeenCalledWith("/briefings/brief-123");
  });

  it("shows submit error when briefing generation fails", async () => {
    vi.mocked(createBriefing).mockRejectedValue(new Error("Request failed"));

    render(
      <BriefingCreateForm
        heading="Generate Supplier Briefing"
        subheading="Run pipeline"
      />
    );

    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(
      screen.getByRole("button", { name: "Generate Briefing" })
    );

    await screen.findByText("Request failed");
  });

  it("shows friendly message when API server is unreachable", async () => {
    vi.mocked(createBriefing).mockRejectedValue(new Error("Failed to fetch"));
    vi.mocked(startBackend).mockRejectedValue(new Error("start failed"));

    render(
      <BriefingCreateForm
        heading="Generate Supplier Briefing"
        subheading="Run pipeline"
      />
    );

    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await screen.findByText(
      "Cannot reach the API server. Make sure the backend is running on port 8000."
    );
  });

  it("auto-starts backend and retries once on network failure", async () => {
    vi.mocked(createBriefing)
      .mockRejectedValueOnce(new Error("Failed to fetch"))
      .mockResolvedValueOnce({
        id: "brief-retry-1",
        created_at: "2026-04-18T12:00:00Z",
        status: "complete"
      });

    render(
      <BriefingCreateForm
        heading="Generate Supplier Briefing"
        subheading="Run pipeline"
      />
    );

    await screen.findByRole("option", { name: "Northstar Foods Co" });
    fireEvent.click(screen.getByRole("button", { name: "Generate Briefing" }));

    await waitFor(() => {
      expect(startBackend).toHaveBeenCalledOnce();
      expect(createBriefing).toHaveBeenCalledTimes(2);
    });
    expect(pushMock).toHaveBeenCalledWith("/briefings/brief-retry-1");
  });
});
