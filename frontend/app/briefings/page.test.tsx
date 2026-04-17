import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import BriefingsPage from "./page";
import { listBriefings } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  listBriefings: vi.fn()
}));

describe("BriefingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders briefing rows when history exists", async () => {
    vi.mocked(listBriefings).mockResolvedValue({
      briefings: [
        {
          id: "b-1",
          created_at: "2026-04-17T12:00:00Z",
          status: "complete",
          vendor: "Kelloggs",
          meeting_date: "2026-04-03"
        }
      ],
      total: 1
    });

    render(<BriefingsPage />);

    expect(await screen.findByText("Kelloggs")).toBeInTheDocument();
    expect(screen.getByText(/Meeting: 2026-04-03/)).toBeInTheDocument();
  });

  it("renders empty-state message when no briefings exist", async () => {
    vi.mocked(listBriefings).mockResolvedValue({
      briefings: [],
      total: 0
    });

    render(<BriefingsPage />);

    expect(await screen.findByText(/No briefings found yet/)).toBeInTheDocument();
  });

  it("renders error message when list call fails", async () => {
    vi.mocked(listBriefings).mockRejectedValue(new Error("history error"));

    render(<BriefingsPage />);

    expect(await screen.findByText("history error")).toBeInTheDocument();
  });
});
