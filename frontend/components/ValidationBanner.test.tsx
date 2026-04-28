import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValidationBanner } from "./ValidationBanner";

describe("ValidationBanner", () => {
  it("renders nothing when no report is provided", () => {
    const { container } = render(<ValidationBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when the report has no errors or warnings", () => {
    const { container } = render(
      <ValidationBanner report={{ overall_status: "passed", errors: [], warnings: [] }} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders error and warning sections when present", () => {
    render(
      <ValidationBanner
        report={{
          overall_status: "failed",
          errors: ["Missing vendor_master.csv"],
          warnings: ["promo_calendar.csv is stale"],
        }}
      />
    );

    expect(screen.getByText("Dataset Validation Failed")).toBeInTheDocument();
    expect(screen.getByText("Missing vendor_master.csv")).toBeInTheDocument();
    expect(screen.getByText("promo_calendar.csv is stale")).toBeInTheDocument();
  });

  it("renders warning-only state", () => {
    render(
      <ValidationBanner
        report={{
          overall_status: "warning",
          errors: [],
          warnings: ["chargebacks.csv is stale"],
        }}
      />
    );

    expect(screen.getByText("Dataset Validation Warnings")).toBeInTheDocument();
    expect(screen.getByText("chargebacks.csv is stale")).toBeInTheDocument();
  });
});
