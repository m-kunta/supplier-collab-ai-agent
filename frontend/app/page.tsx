"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  listVendors,
  createBriefing,
  type VendorRecord,
  type BriefingCreatePayload,
} from "../lib/api";
import styles from "./page.module.css";

const DATA_DIR = "data/inbound/mock";

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function HomePage() {
  const router = useRouter();

  // Vendor list state
  const [vendors, setVendors] = useState<VendorRecord[]>([]);
  const [vendorsLoading, setVendorsLoading] = useState(true);
  const [vendorsError, setVendorsError] = useState<string | null>(null);

  // Form state
  const [vendor, setVendor] = useState("");
  const [meetingDate, setMeetingDate] = useState(todayISO());
  const [lookbackWeeks, setLookbackWeeks] = useState(13);
  const [personaEmphasis, setPersonaEmphasis] = useState<"buyer" | "planner" | "both">("both");
  const [includeBenchmarks, setIncludeBenchmarks] = useState(true);
  const [outputFormat, setOutputFormat] = useState<"md" | "docx" | "both">("md");
  const [categoryFilter, setCategoryFilter] = useState("");

  // Submit state
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    listVendors(DATA_DIR)
      .then((res) => {
        setVendors(res.vendors);
        if (res.vendors.length > 0) {
          setVendor(res.vendors[0].vendor_name);
        }
      })
      .catch((err: unknown) => {
        setVendorsError(
          err instanceof Error ? err.message : "Could not load vendor list"
        );
      })
      .finally(() => setVendorsLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);

    const payload: BriefingCreatePayload = {
      vendor,
      meeting_date: meetingDate,
      data_dir: DATA_DIR,
      lookback_weeks: lookbackWeeks,
      persona_emphasis: personaEmphasis,
      include_benchmarks: includeBenchmarks,
      output_format: outputFormat,
      category_filter: categoryFilter.trim() || null,
    };

    try {
      const result = await createBriefing(payload);
      router.push(`/briefings/${result.id}`);
    } catch (err: unknown) {
      setSubmitError(
        err instanceof Error ? err.message : "Failed to generate briefing"
      );
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.main}>
      <h1 className={styles.heading}>Supplier Briefing Agent</h1>
      <p className={styles.subheading}>
        Pre-meeting intelligence for supplier collaboration
      </p>

      <form className={styles.glassCard} onSubmit={handleSubmit}>
        {/* Vendor */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="vendor">
            Vendor
          </label>
          {vendorsLoading ? (
            <p className={styles.vendorNote}>Loading vendors…</p>
          ) : vendors.length > 0 ? (
            <select
              id="vendor"
              className={styles.select}
              value={vendor}
              onChange={(e) => setVendor(e.target.value)}
              required
            >
              {vendors.map((v) => (
                <option key={v.vendor_id} value={v.vendor_name}>
                  {v.vendor_name}
                </option>
              ))}
            </select>
          ) : (
            <>
              <input
                id="vendor"
                className={styles.input}
                type="text"
                placeholder="e.g. Kelloggs"
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                required
              />
              {vendorsError && (
                <p className={styles.vendorNote}>{vendorsError}</p>
              )}
            </>
          )}
        </div>

        {/* Meeting Date */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="meetingDate">
            Meeting Date
          </label>
          <input
            id="meetingDate"
            className={styles.input}
            type="date"
            value={meetingDate}
            onChange={(e) => setMeetingDate(e.target.value)}
            required
          />
        </div>

        {/* Lookback Weeks */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="lookbackWeeks">
            Lookback Weeks
          </label>
          <input
            id="lookbackWeeks"
            className={styles.input}
            type="number"
            min={1}
            max={52}
            value={lookbackWeeks}
            onChange={(e) => setLookbackWeeks(Number(e.target.value))}
            required
          />
        </div>

        {/* Persona Emphasis */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="personaEmphasis">
            Persona Emphasis
          </label>
          <select
            id="personaEmphasis"
            className={styles.select}
            value={personaEmphasis}
            onChange={(e) =>
              setPersonaEmphasis(e.target.value as "buyer" | "planner" | "both")
            }
          >
            <option value="both">Both (Buyer + Planner)</option>
            <option value="buyer">Buyer</option>
            <option value="planner">Planner</option>
          </select>
        </div>

        {/* Output Format */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="outputFormat">
            Output Format
          </label>
          <select
            id="outputFormat"
            className={styles.select}
            value={outputFormat}
            onChange={(e) =>
              setOutputFormat(e.target.value as "md" | "docx" | "both")
            }
          >
            <option value="md">Markdown</option>
            <option value="docx">DOCX</option>
            <option value="both">Both</option>
          </select>
        </div>

        {/* Include Benchmarks */}
        <div className={styles.field}>
          <label className={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={includeBenchmarks}
              onChange={(e) => setIncludeBenchmarks(e.target.checked)}
            />
            Include Benchmarks
          </label>
        </div>

        {/* Category Filter */}
        <div className={styles.field}>
          <label className={styles.label} htmlFor="categoryFilter">
            Category Filter{" "}
            <span style={{ fontWeight: 400, textTransform: "none" }}>
              (optional)
            </span>
          </label>
          <input
            id="categoryFilter"
            className={styles.input}
            type="text"
            placeholder="e.g. Cereal"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          />
        </div>

        <button className={styles.btn} type="submit" disabled={submitting}>
          {submitting ? "Generating…" : "Generate Briefing"}
        </button>
      </form>

      {submitError && <p className={styles.error}>{submitError}</p>}
    </main>
  );
}
