import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../../components/BriefingCreateForm", () => ({
  BriefingCreateForm: ({ heading, subheading }: { heading: string; subheading: string }) => (
    <div>
      <h1>{heading}</h1>
      <p>{subheading}</p>
    </div>
  ),
}));

describe("NewBriefingPage", () => {
  it("renders the briefing creation form with the expected copy", async () => {
    const { default: NewBriefingPage } = await import("./page");

    render(<NewBriefingPage />);

    expect(screen.getByText("Generate Supplier Briefing")).toBeInTheDocument();
    expect(
      screen.getByText(/Run the pipeline and open a generated briefing with stream replay/)
    ).toBeInTheDocument();
  });
});
