"use client";

import React, { useState } from "react";
import {
  registerVendor,
  RegisteredVendor,
  VendorCreatePayload
} from "../lib/api";

interface Props {
  onRegistered: (vendor: RegisteredVendor) => void;
}

const emptyForm: VendorCreatePayload = {
  vendor_id: "",
  vendor_name: "",
  category: "",
  tier: ""
};

export function VendorRegisterForm({ onRegistered }: Props) {
  const [form, setForm] = useState<VendorCreatePayload>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof VendorCreatePayload, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const saved = await registerVendor(form);
      setForm(emptyForm);
      onRegistered(saved);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  const field = (
    label: string,
    id: keyof VendorCreatePayload,
    placeholder: string
  ) => (
    <div style={{ marginBottom: "1rem" }}>
      <label
        htmlFor={id}
        style={{ display: "block", fontWeight: 600, marginBottom: 4 }}
      >
        {label}
      </label>
      <input
        id={id}
        value={form[id]}
        onChange={(event) => set(id, event.target.value)}
        placeholder={placeholder}
        required
        style={{
          width: "100%",
          padding: "0.5rem",
          border: "1px solid #d1d5db",
          borderRadius: 6,
          fontSize: "0.95rem",
          boxSizing: "border-box"
        }}
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} aria-label="vendor registration">
      {error && (
        <div
          role="alert"
          style={{
            background: "#fef2f2",
            border: "1px solid #fca5a5",
            padding: "0.75rem",
            borderRadius: 6,
            marginBottom: "1rem",
            color: "#b91c1c"
          }}
        >
          {error}
        </div>
      )}

      {field("Vendor ID", "vendor_id", "e.g. VEN001")}
      {field("Vendor Name", "vendor_name", "e.g. Northstar Foods Co")}
      {field("Category", "category", "e.g. Grocery")}
      {field("Tier", "tier", "e.g. Tier 1")}

      <button
        type="submit"
        disabled={submitting}
        style={{
          padding: "0.6rem 1.5rem",
          background: submitting ? "#9ca3af" : "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          fontWeight: 600,
          cursor: submitting ? "not-allowed" : "pointer",
          fontSize: "0.95rem"
        }}
      >
        {submitting ? "Registering..." : "Register Vendor"}
      </button>
    </form>
  );
}
