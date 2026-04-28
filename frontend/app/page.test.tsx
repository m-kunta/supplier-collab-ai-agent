import { describe, expect, it, vi } from "vitest";

const redirectMock = vi.fn();

vi.mock("next/navigation", () => ({
  redirect: (...args: unknown[]) => redirectMock(...args),
}));

describe("HomePage", () => {
  it("redirects to the new briefing flow", async () => {
    const { default: HomePage } = await import("./page");

    HomePage();

    expect(redirectMock).toHaveBeenCalledWith("/briefings/new");
  });
});
