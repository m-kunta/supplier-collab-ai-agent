import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RootLayout, { metadata } from "./layout";

describe("RootLayout", () => {
  it("exports the expected metadata", () => {
    expect(metadata.title).toBe("Supplier Briefing Agent");
    expect(metadata.description).toContain("supplier collaboration");
  });

  it("renders children inside the document body", () => {
    render(
      <RootLayout>
        <div>Child content</div>
      </RootLayout>
    );

    expect(screen.getByText("Child content")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });
});
