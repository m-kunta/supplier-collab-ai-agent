import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import VendorsPage from "./page";
import {
  downloadOnboardingPack,
  listRegisteredVendors,
  registerVendor
} from "../../lib/api";

vi.mock("../../lib/api", () => ({
  downloadOnboardingPack: vi.fn(),
  listRegisteredVendors: vi.fn(),
  registerVendor: vi.fn()
}));

const mockVendor = {
  id: "u1",
  vendor_id: "VEN001",
  vendor_name: "Northstar Foods Co",
  category: "Grocery",
  tier: "Tier 1",
  status: "pending_data",
  created_at: "2026-05-11T00:00:00Z"
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listRegisteredVendors).mockResolvedValue({ vendors: [], total: 0 });
  vi.mocked(downloadOnboardingPack).mockResolvedValue(undefined);
});

function fillRegistrationForm() {
  fireEvent.change(screen.getByLabelText(/vendor id/i), {
    target: { value: "VEN001" }
  });
  fireEvent.change(screen.getByLabelText(/vendor name/i), {
    target: { value: "Northstar Foods Co" }
  });
  fireEvent.change(screen.getByLabelText(/category/i), {
    target: { value: "Grocery" }
  });
  fireEvent.change(screen.getByLabelText(/tier/i), {
    target: { value: "Tier 1" }
  });
}

describe("VendorsPage", () => {
  it("renders page heading", () => {
    render(<VendorsPage />);

    expect(
      screen.getByRole("heading", { name: /vendor onboarding/i })
    ).toBeInTheDocument();
  });

  it("shows empty state when no vendors are registered", async () => {
    render(<VendorsPage />);

    await waitFor(() =>
      expect(screen.getByText(/no vendors registered/i)).toBeInTheDocument()
    );
  });

  it("renders vendor row after load", async () => {
    vi.mocked(listRegisteredVendors).mockResolvedValue({
      vendors: [mockVendor],
      total: 1
    });

    render(<VendorsPage />);

    await waitFor(() =>
      expect(screen.getByText("Northstar Foods Co")).toBeInTheDocument()
    );
    expect(screen.getByText("VEN001")).toBeInTheDocument();
    expect(screen.getByText("pending_data")).toBeInTheDocument();
  });

  it("calls downloadOnboardingPack when Download Pack is clicked", async () => {
    vi.mocked(listRegisteredVendors).mockResolvedValue({
      vendors: [mockVendor],
      total: 1
    });

    render(<VendorsPage />);

    await waitFor(() => screen.getByText("Northstar Foods Co"));
    fireEvent.click(screen.getByRole("button", { name: /download pack/i }));

    await waitFor(() =>
      expect(downloadOnboardingPack).toHaveBeenCalledWith("VEN001")
    );
  });

  it("adds newly registered vendor to the table", async () => {
    vi.mocked(registerVendor).mockResolvedValueOnce(mockVendor);

    render(<VendorsPage />);

    await waitFor(() => screen.getByText(/no vendors registered/i));
    fillRegistrationForm();
    fireEvent.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() =>
      expect(screen.getByText("Northstar Foods Co")).toBeInTheDocument()
    );
    expect(registerVendor).toHaveBeenCalledWith({
      vendor_id: "VEN001",
      vendor_name: "Northstar Foods Co",
      category: "Grocery",
      tier: "Tier 1"
    });
  });

  it("shows load error when registered vendors cannot be loaded", async () => {
    vi.mocked(listRegisteredVendors).mockRejectedValueOnce(
      new Error("registry unavailable")
    );

    render(<VendorsPage />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("registry unavailable")
    );
  });
});
