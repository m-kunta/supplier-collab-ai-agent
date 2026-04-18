import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BackendStatus } from "./BackendStatus";
import { checkHealth } from "../lib/api";

vi.mock("../lib/api", () => ({
  checkHealth: vi.fn()
}));

describe("BackendStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows nothing while checking", () => {
    vi.mocked(checkHealth).mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = render(<BackendStatus />);
    expect(container.firstChild).toBeNull();
  });

  it("shows API online badge when health check passes", async () => {
    vi.mocked(checkHealth).mockResolvedValue(true);
    render(<BackendStatus />);
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });

  it("shows API offline badge and Start Backend button when health check fails", async () => {
    vi.mocked(checkHealth).mockResolvedValue(false);
    render(<BackendStatus />);
    expect(await screen.findByText("API offline")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start Backend" })).toBeInTheDocument();
  });

  it("calls /api/start-backend on button click and rechecks health", async () => {
    vi.mocked(checkHealth).mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    render(<BackendStatus />);
    const btn = await screen.findByRole("button", { name: "Start Backend" });
    fireEvent.click(btn);

    expect(await screen.findByText("API online")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/start-backend", { method: "POST" });
  });

  it("shows Starting… while the start request is in flight", async () => {
    vi.mocked(checkHealth).mockResolvedValue(false);
    vi.mocked(fetch).mockReturnValue(new Promise(() => {})); // never resolves

    render(<BackendStatus />);
    const btn = await screen.findByRole("button", { name: "Start Backend" });
    fireEvent.click(btn);

    expect(await screen.findByRole("button", { name: "Starting…" })).toBeDisabled();
  });

  it("recovers to offline when start-backend fetch throws", async () => {
    vi.mocked(checkHealth).mockResolvedValue(false);
    vi.mocked(fetch).mockRejectedValue(new Error("network error"));

    render(<BackendStatus />);
    const btn = await screen.findByRole("button", { name: "Start Backend" });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(screen.getByText("API offline")).toBeInTheDocument();
    });
  });
});
