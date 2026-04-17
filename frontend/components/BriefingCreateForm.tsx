"use client";

import React from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createBriefing,
  listVendors,
  type BriefingCreatePayload,
  type VendorRecord
} from "../lib/api";
import styles from "./briefing-create-form.module.css";
import { AppHeader } from "./AppHeader";

const DATA_DIR = "data/inbound/mock";

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

type Props = {
  heading: string;
  subheading: string;
};

export function BriefingCreateForm({ heading, subheading }: Props) {
  const router = useRouter();
  const [vendors, setVendors] = useState<VendorRecord[]>([]);
  const [vendorsLoading, setVendorsLoading] = useState(true);
  const [vendorsError, setVendorsError] = useState<string | null>(null);

  const [vendor, setVendor] = useState("");
  const [meetingDate, setMeetingDate] = useState(todayISO());
  const [lookbackWeeks, setLookbackWeeks] = useState(13);
  const [personaEmphasis, setPersonaEmphasis] = useState<"buyer" | "planner" | "both">("both");
  const [includeBenchmarks, setIncludeBenchmarks] = useState(true);
  const [outputFormat, setOutputFormat] = useState<"md" | "docx" | "both">("md");
  const [categoryFilter, setCategoryFilter] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    listVendors(DATA_DIR)
      .then((res) => {
        if (!mounted) {
          return;
        }
        setVendors(res.vendors);
        if (res.vendors.length > 0) {
          setVendor(res.vendors[0].vendor_name ?? res.vendors[0].vendor_id);
        }
      })
      .catch((err: unknown) => {
        if (!mounted) {
          return;
        }
        setVendorsError(err instanceof Error ? err.message : "Could not load vendor list");
      })
      .finally(() => {
        if (mounted) {
          setVendorsLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);

    const payload: BriefingCreatePayload = {
      vendor,
      meeting_date: meetingDate,
      data_dir: DATA_DIR,
      lookback_weeks: lookbackWeeks,
      persona_emphasis: personaEmphasis,
      include_benchmarks: includeBenchmarks,
      output_format: outputFormat,
      category_filter: categoryFilter.trim() || null
    };

    try {
      const result = await createBriefing(payload);
      router.push(`/briefings/${result.id}`);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Failed to generate briefing");
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <AppHeader />
        <section className={styles.intro}>
          <h1 className={styles.heading}>{heading}</h1>
          <p className={styles.subheading}>{subheading}</p>
        </section>

        <form className={styles.card} onSubmit={handleSubmit}>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="vendor">
              Vendor
            </label>
            {vendorsLoading ? (
              <p className={styles.note}>Loading vendors...</p>
            ) : vendors.length > 0 ? (
              <select
                id="vendor"
                className={styles.select}
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                required
              >
                {vendors.map((v) => (
                  <option key={v.vendor_id} value={v.vendor_name ?? v.vendor_id}>
                    {v.vendor_name ?? v.vendor_id}
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
                {vendorsError && <p className={styles.note}>{vendorsError}</p>}
              </>
            )}
          </div>

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

          <div className={styles.field}>
            <label className={styles.label} htmlFor="personaEmphasis">
              Persona Emphasis
            </label>
            <select
              id="personaEmphasis"
              className={styles.select}
              value={personaEmphasis}
              onChange={(e) => setPersonaEmphasis(e.target.value as "buyer" | "planner" | "both")}
            >
              <option value="both">Both (Buyer + Planner)</option>
              <option value="buyer">Buyer</option>
              <option value="planner">Planner</option>
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="outputFormat">
              Output Format
            </label>
            <select
              id="outputFormat"
              className={styles.select}
              value={outputFormat}
              onChange={(e) => setOutputFormat(e.target.value as "md" | "docx" | "both")}
            >
              <option value="md">Markdown</option>
              <option value="docx">DOCX</option>
              <option value="both">Both</option>
            </select>
          </div>

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

          <div className={styles.field}>
            <label className={styles.label} htmlFor="categoryFilter">
              Category Filter (optional)
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

          <button className={styles.cta} type="submit" disabled={submitting}>
            {submitting ? "Generating..." : "Generate Briefing"}
          </button>
          {submitError && <p className={styles.error}>{submitError}</p>}
        </form>
      </div>
    </main>
  );
}
