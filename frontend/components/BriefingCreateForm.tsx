"use client";

import React from "react";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  createBriefingStreaming,
  startBackend,
  listVendors,
  type BriefingCreatePayload,
  type VendorRecord,
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

  // Streaming state
  const [phase, setPhase] = useState<"idle" | "engines" | "streaming" | "done" | "error">("idle");
  const [streamPreview, setStreamPreview] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  const submitting = phase === "engines" || phase === "streaming";

  useEffect(() => {
    let mounted = true;
    listVendors(DATA_DIR)
      .then((res) => {
        if (!mounted) return;
        setVendors(res.vendors);
        if (res.vendors.length > 0) {
          setVendor(res.vendors[0].vendor_name ?? res.vendors[0].vendor_id);
        }
      })
      .catch((err: unknown) => {
        if (!mounted) return;
        setVendorsError(err instanceof Error ? err.message : "Could not load vendor list");
      })
      .finally(() => {
        if (mounted) setVendorsLoading(false);
      });
    return () => { mounted = false; };
  }, []);

  // Auto-scroll the preview pane as tokens arrive
  useEffect(() => {
    if (previewRef.current) {
      previewRef.current.scrollTop = previewRef.current.scrollHeight;
    }
  }, [streamPreview]);

  async function runStream(payload: BriefingCreatePayload) {
    setPhase("engines");
    setStreamPreview("");
    setSubmitError(null);

    await createBriefingStreaming(payload, {
      onEngines: () => {
        // Engines data is embedded in the done summary; switch UI to streaming phase
        setPhase("streaming");
      },
      onToken: (chunk) => {
        setStreamPreview((prev) => prev + chunk);
      },
      onDone: (briefing) => {
        setPhase("done");
        router.push(`/briefings/${briefing.id}`);
      },
      onError: (message) => {
        setPhase("error");
        setSubmitError(message);
      },
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

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
      await runStream(payload);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Failed to generate briefing";

      // Network failure — try to auto-start the backend then retry once
      if (raw === "Failed to fetch") {
        try {
          await startBackend();
          await runStream(payload);
          return;
        } catch {
          setPhase("error");
          setSubmitError(
            "Cannot reach the API server. Make sure the backend is running on port 8000."
          );
          return;
        }
      }

      setPhase("error");
      setSubmitError(raw);
    }
  }

  const statusLabel =
    phase === "engines"
      ? "Running compute engines…"
      : phase === "streaming"
      ? "Streaming briefing…"
      : phase === "done"
      ? "Done — redirecting…"
      : null;

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
                  placeholder="e.g. Northstar Foods Co"
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

          <button
            className={styles.cta}
            type="submit"
            id="generate-briefing-btn"
            disabled={submitting}
          >
            {submitting ? "Generating…" : "Generate Briefing"}
          </button>

          {statusLabel && (
            <p className={styles.status} aria-live="polite">
              {statusLabel}
            </p>
          )}

          {(phase === "streaming" || phase === "done") && streamPreview && (
            <div className={styles.streamWrap}>
              <p className={styles.streamLabel}>
                Live preview
                {phase === "streaming" && (
                  <span className={styles.cursor} aria-hidden="true" />
                )}
              </p>
              <div ref={previewRef} className={styles.streamBox} aria-label="streaming preview">
                {streamPreview}
              </div>
            </div>
          )}

          {submitError && <p className={styles.error}>{submitError}</p>}
        </form>
      </div>
    </main>
  );
}
