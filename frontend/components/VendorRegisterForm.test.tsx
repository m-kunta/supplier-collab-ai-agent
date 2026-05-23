import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { VendorRegisterForm } from "./VendorRegisterForm";
import { registerVendor } from "../lib/api";

vi.mock("../lib/api", () => ({
  registerVendor: vi.fn()
}));

const mockOnRegistered = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
});

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/vendor id/i), {
    target: { value: "VEN001" }
  });
  fireEvent.change(screen.getByLabelText(/vendor name/i), {
    target: { value: "Northstar" }
  });
  fireEvent.change(screen.getByLabelText(/category/i), {
    target: { value: "Grocery" }
  });
  fireEvent.change(screen.getByLabelText(/tier/i), {
    target: { value: "Tier 1" }
  });
}

describe("VendorRegisterForm", () => {
  it("renders all form fields", () => {
    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);

    expect(screen.getByLabelText(/vendor id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/vendor name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tier/i)).toBeInTheDocument();
  });

  it("calls onRegistered with form values on submit", async () => {
    vi.mocked(registerVendor).mockResolvedValueOnce({
      id: "u1",
      vendor_id: "VEN001",
      vendor_name: "Northstar",
      category: "Grocery",
      tier: "Tier 1",
      status: "pending_data",
      created_at: "2026-05-11T00:00:00Z"
    });

    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() =>
      expect(mockOnRegistered).toHaveBeenCalledWith(
        expect.objectContaining({ vendor_id: "VEN001" })
      )
    );
  });

  it("shows error message on duplicate vendor", async () => {
    vi.mocked(registerVendor).mockRejectedValueOnce(new Error("already exists"));

    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() =>
      expect(screen.getByText(/already exists/i)).toBeInTheDocument()
    );
  });

  it("disables submit button while submitting", () => {
    vi.mocked(registerVendor).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                id: "u1",
                vendor_id: "VEN001",
                vendor_name: "Northstar",
                category: "Grocery",
                tier: "Tier 1",
                status: "pending_data",
                created_at: "2026-05-11T00:00:00Z"
              }),
            200
          )
        )
    );

    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /register/i }));

    expect(screen.getByRole("button", { name: /registering/i })).toBeDisabled();
  });

  it("clears form after successful registration", async () => {
    vi.mocked(registerVendor).mockResolvedValueOnce({
      id: "u1",
      vendor_id: "VEN001",
      vendor_name: "Northstar",
      category: "Grocery",
      tier: "Tier 1",
      status: "pending_data",
      created_at: "2026-05-11T00:00:00Z"
    });

    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: /register/i }));

    await waitFor(() =>
      expect((screen.getByLabelText(/vendor id/i) as HTMLInputElement).value).toBe("")
    );
  });
});
