"use client";

import React, { useEffect, useState } from "react";
import {
  downloadOnboardingPack,
  listRegisteredVendors,
  RegisteredVendor
} from "../../lib/api";
import { VendorRegisterForm } from "../../components/VendorRegisterForm";

export default function VendorsPage() {
  const [vendors, setVendors] = useState<RegisteredVendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadVendors() {
      try {
        const result = await listRegisteredVendors();
        if (!cancelled) setVendors(result.vendors);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load vendors");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadVendors();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRegistered = (vendor: RegisteredVendor) => {
    setVendors((current) => [...current, vendor]);
  };

  const handleDownload = async (vendorId: string) => {
    setDownloading(vendorId);
    setError(null);

    try {
      await downloadOnboardingPack(vendorId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <main style={{ maxWidth: 900, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Vendor Onboarding</h1>
      <p style={{ color: "#64748b", fontSize: "0.875rem" }}>
        Prototype vendor registry backed by <code>config/vendors.json</code>.
      </p>

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

      <section
        style={{
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: 8,
          padding: "1.5rem",
          marginBottom: "2rem"
        }}
      >
        <h2 style={{ marginTop: 0 }}>Register New Vendor</h2>
        <VendorRegisterForm onRegistered={handleRegistered} />
      </section>

      <section>
        <h2>Registered Vendors</h2>
        {loading ? (
          <p style={{ color: "#64748b" }}>Loading...</p>
        ) : vendors.length === 0 ? (
          <p style={{ color: "#64748b" }}>No vendors registered yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
                {["Vendor ID", "Name", "Category", "Tier", "Status", "Registered", ""].map(
                  (heading) => (
                    <th
                      key={heading}
                      style={{
                        textAlign: "left",
                        padding: "0.5rem 0.75rem",
                        fontSize: "0.85rem",
                        color: "#6b7280",
                        fontWeight: 600
                      }}
                    >
                      {heading}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {vendors.map((vendor) => (
                <tr key={vendor.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "0.6rem 0.75rem", fontFamily: "monospace" }}>
                    {vendor.vendor_id}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", fontWeight: 500 }}>
                    {vendor.vendor_name}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>{vendor.category}</td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>{vendor.tier}</td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span
                      style={{
                        background: "#fef9c3",
                        color: "#92400e",
                        borderRadius: 4,
                        padding: "0.2rem 0.5rem",
                        fontSize: "0.8rem"
                      }}
                    >
                      {vendor.status}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: "0.6rem 0.75rem",
                      color: "#64748b",
                      fontSize: "0.85rem"
                    }}
                  >
                    {new Date(vendor.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <button
                      onClick={() => handleDownload(vendor.vendor_id)}
                      disabled={downloading === vendor.vendor_id}
                      style={{
                        padding: "0.35rem 0.85rem",
                        background: "#2563eb",
                        color: "#fff",
                        border: "none",
                        borderRadius: 5,
                        cursor:
                          downloading === vendor.vendor_id ? "not-allowed" : "pointer",
                        fontSize: "0.85rem",
                        opacity: downloading === vendor.vendor_id ? 0.6 : 1
                      }}
                    >
                      {downloading === vendor.vendor_id
                        ? "Downloading..."
                        : "Download Pack"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
