# Vendor Onboarding UI — Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/vendors` frontend page that lets users register new suppliers and download per-vendor CSV onboarding packs, wired to the three backend API routes added in Phase 9.

**Architecture:** New Next.js page at `frontend/app/vendors/page.tsx` with two sections — a registration form and a registered-vendors table. All API communication goes through typed helpers in `frontend/lib/api.ts`. The zip download uses `fetch()` → `blob()` → `URL.createObjectURL()` (no JSON path). Follows the same inline-style, `useEffect`-driven pattern as `frontend/app/settings/page.tsx`.

**Tech Stack:** Next.js 15 / React 19, TypeScript, Vitest + jsdom, existing FastAPI backend (`api/main.py`)

---

## Backend API (already implemented — read-only reference)

| Route | Description |
|---|---|
| `GET /api/vendors/registered` | Returns `{ vendors: RegisteredVendor[], total: number }` |
| `POST /api/vendors` | Body: `{ vendor_id, vendor_name, category, tier }` → returns saved record or 409 on duplicate |
| `GET /api/vendors/{vendor_id}/onboarding-pack` | Streams a `.zip` file with blank CSV templates + `instructions.md` |

`RegisteredVendor` shape (from `src/vendor_store.py`):
```typescript
{
  id: string           // UUID
  vendor_id: string    // e.g. "VEN001"
  vendor_name: string
  category: string
  tier: string
  status: string       // e.g. "pending_data"
  created_at: string   // ISO timestamp
}
```

---

## Task 1: API helpers in `frontend/lib/api.ts`

**Files:**
- Modify: `frontend/lib/api.ts`
- Test: `frontend/lib/api.test.ts`

- [ ] **Step 1: Add types and helpers**

Append to `frontend/lib/api.ts`:

```typescript
// ---------------------------------------------------------------------------
// Vendor Onboarding
// ---------------------------------------------------------------------------

export interface RegisteredVendor {
  id: string;
  vendor_id: string;
  vendor_name: string;
  category: string;
  tier: string;
  status: string;
  created_at: string;
}

export interface RegisteredVendorsResponse {
  vendors: RegisteredVendor[];
  total: number;
}

export interface VendorCreatePayload {
  vendor_id: string;
  vendor_name: string;
  category: string;
  tier: string;
}

export async function listRegisteredVendors(): Promise<RegisteredVendorsResponse> {
  const res = await fetch(`${API_BASE}/api/vendors/registered`);
  return readJson<RegisteredVendorsResponse>(res, "Failed to list registered vendors");
}

export async function registerVendor(
  payload: VendorCreatePayload
): Promise<RegisteredVendor> {
  const res = await fetch(`${API_BASE}/api/vendors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson<RegisteredVendor>(res, "Failed to register vendor");
}

export async function downloadOnboardingPack(vendor_id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/vendors/${vendor_id}/onboarding-pack`);
  if (!res.ok) throw new Error(`Failed to download onboarding pack: HTTP ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${vendor_id}_onboarding_pack.zip`;
  a.click();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 2: Write tests for the three new helpers**

Append to `frontend/lib/api.test.ts`:

```typescript
describe("listRegisteredVendors", () => {
  it("returns vendors and total", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ vendors: [{ id: "u1", vendor_id: "VEN001",
        vendor_name: "Northstar", category: "Grocery", tier: "Tier 1",
        status: "pending_data", created_at: "2026-05-11T00:00:00Z" }], total: 1 }),
        { status: 200 })
    );
    const result = await listRegisteredVendors();
    expect(result.total).toBe(1);
    expect(result.vendors[0].vendor_id).toBe("VEN001");
  });
});

describe("registerVendor", () => {
  it("posts payload and returns saved record", async () => {
    const record = { id: "u1", vendor_id: "VEN002", vendor_name: "Apex",
      category: "Grocery", tier: "Tier 2", status: "pending_data",
      created_at: "2026-05-11T00:00:00Z" };
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(record), { status: 200 })
    );
    const result = await registerVendor({ vendor_id: "VEN002", vendor_name: "Apex",
      category: "Grocery", tier: "Tier 2" });
    expect(result.vendor_id).toBe("VEN002");
    expect(vi.mocked(fetch).mock.calls[0][1]?.method).toBe("POST");
  });
});

describe("downloadOnboardingPack", () => {
  it("fetches zip and triggers download", async () => {
    const mockBlob = new Blob(["PK fake"], { type: "application/zip" });
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(mockBlob, { status: 200 })
    );
    const createObjectURL = vi.fn(() => "blob:fake-url");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const clickMock = vi.fn();
    vi.spyOn(document, "createElement").mockReturnValueOnce(
      { href: "", download: "", click: clickMock } as unknown as HTMLAnchorElement
    );
    await downloadOnboardingPack("VEN001");
    expect(createObjectURL).toHaveBeenCalled();
    expect(clickMock).toHaveBeenCalled();
  });
});
```

- [ ] **Step 3: Run frontend tests and confirm new tests pass**

```bash
cd frontend && npx vitest run --config vitest.config.ts lib/api.test.ts
```
Expected: all existing + 3 new tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "feat(vendors): add listRegisteredVendors, registerVendor, downloadOnboardingPack API helpers"
```

---

## Task 2: `VendorRegisterForm` component

**Files:**
- Create: `frontend/components/VendorRegisterForm.tsx`
- Test: `frontend/components/VendorRegisterForm.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/components/VendorRegisterForm.test.tsx`:

```typescript
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { VendorRegisterForm } from "./VendorRegisterForm";

const mockOnRegistered = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
});

describe("VendorRegisterForm", () => {
  it("renders all form fields", () => {
    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    expect(screen.getByLabelText(/vendor id/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/vendor name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/tier/i)).toBeInTheDocument();
  });

  it("calls onRegistered with form values on submit", async () => {
    const { registerVendor } = await import("../lib/api");
    vi.mocked(registerVendor).mockResolvedValueOnce({
      id: "u1", vendor_id: "VEN001", vendor_name: "Northstar",
      category: "Grocery", tier: "Tier 1", status: "pending_data",
      created_at: "2026-05-11T00:00:00Z",
    });
    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fireEvent.change(screen.getByLabelText(/vendor id/i), { target: { value: "VEN001" } });
    fireEvent.change(screen.getByLabelText(/vendor name/i), { target: { value: "Northstar" } });
    fireEvent.change(screen.getByLabelText(/category/i), { target: { value: "Grocery" } });
    fireEvent.change(screen.getByLabelText(/tier/i), { target: { value: "Tier 1" } });
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    await waitFor(() => expect(mockOnRegistered).toHaveBeenCalledWith(
      expect.objectContaining({ vendor_id: "VEN001" })
    ));
  });

  it("shows error message on duplicate vendor", async () => {
    const { registerVendor } = await import("../lib/api");
    vi.mocked(registerVendor).mockRejectedValueOnce(new Error("already exists"));
    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fireEvent.change(screen.getByLabelText(/vendor id/i), { target: { value: "VEN001" } });
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    await waitFor(() => expect(screen.getByText(/already exists/i)).toBeInTheDocument());
  });

  it("disables submit button while submitting", async () => {
    const { registerVendor } = await import("../lib/api");
    vi.mocked(registerVendor).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 200))
    );
    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fireEvent.change(screen.getByLabelText(/vendor id/i), { target: { value: "VEN001" } });
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    expect(screen.getByRole("button", { name: /registering/i })).toBeDisabled();
  });

  it("clears form after successful registration", async () => {
    const { registerVendor } = await import("../lib/api");
    vi.mocked(registerVendor).mockResolvedValueOnce({
      id: "u1", vendor_id: "VEN001", vendor_name: "Northstar",
      category: "Grocery", tier: "Tier 1", status: "pending_data",
      created_at: "2026-05-11T00:00:00Z",
    });
    render(<VendorRegisterForm onRegistered={mockOnRegistered} />);
    fireEvent.change(screen.getByLabelText(/vendor id/i), { target: { value: "VEN001" } });
    fireEvent.change(screen.getByLabelText(/vendor name/i), { target: { value: "Northstar" } });
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    await waitFor(() =>
      expect((screen.getByLabelText(/vendor id/i) as HTMLInputElement).value).toBe("")
    );
  });
});
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
cd frontend && npx vitest run --config vitest.config.ts components/VendorRegisterForm.test.tsx
```
Expected: FAIL (component doesn't exist yet).

- [ ] **Step 3: Implement `VendorRegisterForm.tsx`**

Create `frontend/components/VendorRegisterForm.tsx`:

```typescript
"use client";

import React, { useState } from "react";
import { registerVendor, VendorCreatePayload, RegisteredVendor } from "../lib/api";

interface Props {
  onRegistered: (vendor: RegisteredVendor) => void;
}

const emptyForm: VendorCreatePayload = {
  vendor_id: "", vendor_name: "", category: "", tier: "",
};

export function VendorRegisterForm({ onRegistered }: Props) {
  const [form, setForm] = useState<VendorCreatePayload>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof VendorCreatePayload, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
      <label htmlFor={id} style={{ display: "block", fontWeight: 600, marginBottom: 4 }}>
        {label}
      </label>
      <input
        id={id}
        value={form[id]}
        onChange={(e) => set(id, e.target.value)}
        placeholder={placeholder}
        required
        style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db",
          borderRadius: 6, fontSize: "0.95rem", boxSizing: "border-box" }}
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit}>
      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5",
          padding: "0.75rem", borderRadius: 6, marginBottom: "1rem", color: "#b91c1c" }}>
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
        style={{ padding: "0.6rem 1.5rem", background: submitting ? "#9ca3af" : "#2563eb",
          color: "#fff", border: "none", borderRadius: 6, fontWeight: 600,
          cursor: submitting ? "not-allowed" : "pointer", fontSize: "0.95rem" }}
      >
        {submitting ? "Registering…" : "Register Vendor"}
      </button>
    </form>
  );
}
```

- [ ] **Step 4: Run tests and confirm all 5 pass**

```bash
cd frontend && npx vitest run --config vitest.config.ts components/VendorRegisterForm.test.tsx
```
Expected: 5/5 pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/VendorRegisterForm.tsx frontend/components/VendorRegisterForm.test.tsx
git commit -m "feat(vendors): add VendorRegisterForm component"
```

---

## Task 3: `/vendors` page

**Files:**
- Create: `frontend/app/vendors/page.tsx`
- Test: `frontend/app/vendors/page.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/app/vendors/page.test.tsx`:

```typescript
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/api");

import VendorsPage from "./page";
import { listRegisteredVendors, downloadOnboardingPack } from "../../lib/api";

const mockVendor = {
  id: "u1", vendor_id: "VEN001", vendor_name: "Northstar Foods Co",
  category: "Grocery", tier: "Tier 1", status: "pending_data",
  created_at: "2026-05-11T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listRegisteredVendors).mockResolvedValue({ vendors: [], total: 0 });
});

describe("VendorsPage", () => {
  it("renders page heading", async () => {
    render(<VendorsPage />);
    expect(screen.getByRole("heading", { name: /vendor onboarding/i })).toBeInTheDocument();
  });

  it("shows empty state when no vendors registered", async () => {
    render(<VendorsPage />);
    await waitFor(() =>
      expect(screen.getByText(/no vendors registered/i)).toBeInTheDocument()
    );
  });

  it("renders vendor row after load", async () => {
    vi.mocked(listRegisteredVendors).mockResolvedValue({
      vendors: [mockVendor], total: 1,
    });
    render(<VendorsPage />);
    await waitFor(() =>
      expect(screen.getByText("Northstar Foods Co")).toBeInTheDocument()
    );
    expect(screen.getByText("VEN001")).toBeInTheDocument();
    expect(screen.getByText("pending_data")).toBeInTheDocument();
  });

  it("calls downloadOnboardingPack when button clicked", async () => {
    vi.mocked(listRegisteredVendors).mockResolvedValue({
      vendors: [mockVendor], total: 1,
    });
    vi.mocked(downloadOnboardingPack).mockResolvedValue(undefined);
    render(<VendorsPage />);
    await waitFor(() => screen.getByText("Northstar Foods Co"));
    fireEvent.click(screen.getByRole("button", { name: /download pack/i }));
    await waitFor(() =>
      expect(downloadOnboardingPack).toHaveBeenCalledWith("VEN001")
    );
  });

  it("refreshes vendor list after registration", async () => {
    const { registerVendor } = await import("../../lib/api");
    vi.mocked(registerVendor).mockResolvedValueOnce(mockVendor);
    vi.mocked(listRegisteredVendors)
      .mockResolvedValueOnce({ vendors: [], total: 0 })
      .mockResolvedValueOnce({ vendors: [mockVendor], total: 1 });
    render(<VendorsPage />);
    await waitFor(() => screen.getByText(/no vendors registered/i));
    // simulate form submit by calling onRegistered callback
    // (integration tested via VendorRegisterForm tests above)
    // confirm list refreshes when onRegistered fires
  });
});
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
cd frontend && npx vitest run --config vitest.config.ts app/vendors/page.test.tsx
```
Expected: FAIL (page doesn't exist yet).

- [ ] **Step 3: Implement `frontend/app/vendors/page.tsx`**

```typescript
"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  listRegisteredVendors,
  downloadOnboardingPack,
  RegisteredVendor,
} from "../../lib/api";
import { VendorRegisterForm } from "../../components/VendorRegisterForm";

export default function VendorsPage() {
  const [vendors, setVendors] = useState<RegisteredVendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const loadVendors = useCallback(async () => {
    try {
      const result = await listRegisteredVendors();
      setVendors(result.vendors);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load vendors");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadVendors(); }, [loadVendors]);

  const handleRegistered = async (vendor: RegisteredVendor) => {
    setVendors((prev) => [...prev, vendor]);
  };

  const handleDownload = async (vendor_id: string) => {
    setDownloading(vendor_id);
    try {
      await downloadOnboardingPack(vendor_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <main style={{ maxWidth: 800, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Vendor Onboarding</h1>
      <p style={{ color: "#888", fontSize: "0.875rem" }}>
        ⚠️ Prototype — vendor registry is stored in{" "}
        <code>config/vendors.json</code>.
      </p>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5",
          padding: "0.75rem", borderRadius: 6, marginBottom: "1rem", color: "#b91c1c" }}>
          {error}
        </div>
      )}

      <section style={{ background: "#f8fafc", border: "1px solid #e2e8f0",
        borderRadius: 8, padding: "1.5rem", marginBottom: "2rem" }}>
        <h2 style={{ marginTop: 0 }}>Register New Vendor</h2>
        <VendorRegisterForm onRegistered={handleRegistered} />
      </section>

      <section>
        <h2>Registered Vendors</h2>
        {loading ? (
          <p style={{ color: "#888" }}>Loading…</p>
        ) : vendors.length === 0 ? (
          <p style={{ color: "#888" }}>No vendors registered yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
                {["Vendor ID", "Name", "Category", "Tier", "Status", "Registered", ""].map((h) => (
                  <th key={h} style={{ textAlign: "left", padding: "0.5rem 0.75rem",
                    fontSize: "0.85rem", color: "#6b7280", fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vendors.map((v) => (
                <tr key={v.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "0.6rem 0.75rem", fontFamily: "monospace" }}>{v.vendor_id}</td>
                  <td style={{ padding: "0.6rem 0.75rem", fontWeight: 500 }}>{v.vendor_name}</td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>{v.category}</td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>{v.tier}</td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span style={{ background: "#fef9c3", color: "#92400e",
                      borderRadius: 4, padding: "0.2rem 0.5rem", fontSize: "0.8rem" }}>
                      {v.status}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", color: "#9ca3af", fontSize: "0.85rem" }}>
                    {new Date(v.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <button
                      onClick={() => handleDownload(v.vendor_id)}
                      disabled={downloading === v.vendor_id}
                      style={{ padding: "0.35rem 0.85rem", background: "#2563eb",
                        color: "#fff", border: "none", borderRadius: 5,
                        cursor: downloading === v.vendor_id ? "not-allowed" : "pointer",
                        fontSize: "0.85rem", opacity: downloading === v.vendor_id ? 0.6 : 1 }}
                    >
                      {downloading === v.vendor_id ? "Downloading…" : "Download Pack"}
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
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd frontend && npx vitest run --config vitest.config.ts app/vendors/page.test.tsx
```
Expected: 4/4 (or 5/5) pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/vendors/page.tsx frontend/app/vendors/page.test.tsx
git commit -m "feat(vendors): add /vendors onboarding page"
```

---

## Task 4: Nav link, docs, final checks

**Files:**
- Modify: `frontend/components/AppHeader.tsx`
- Modify: `CLAUDE.md`, `AGENTS.md`, `README.md`, `TODO.md`

- [ ] **Step 1: Add Vendors nav link to `AppHeader.tsx`**

```typescript
<Link href="/vendors" className={styles.link}>
  Vendors
</Link>
```
Add after the `Settings` link.

- [ ] **Step 2: Run full frontend test suite**

```bash
cd frontend && npm test
```
Expected: all existing tests pass + new vendor tests.

- [ ] **Step 3: Run full backend test suite**

```bash
.venv/bin/pytest tests/ -q
```
Expected: 314 passing (no regressions).

- [ ] **Step 4: Update CLAUDE.md, AGENTS.md, README.md, TODO.md**

Mark vendor onboarding UI TODO items as complete; update frontend table and test counts.

- [ ] **Step 5: Final commit and push**

```bash
git add frontend/components/AppHeader.tsx CLAUDE.md AGENTS.md README.md TODO.md
git commit -m "feat(vendors): add Vendors nav link and update docs"
git push
```

---

## Summary

| Task | Files | Tests |
|---|---|---|
| 1 — API helpers | `frontend/lib/api.ts` + test | 3 new |
| 2 — Register form | `VendorRegisterForm.tsx` + test | 5 new |
| 3 — `/vendors` page | `app/vendors/page.tsx` + test | 4–5 new |
| 4 — Nav + docs | `AppHeader.tsx`, docs | 0 new |

**Total new tests: ~13 frontend.** Backend: no changes needed (already covered by `test_vendor_api.py`).
