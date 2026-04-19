"use client";

import React from "react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AppHeader } from "../../../components/AppHeader";
import {
  getBriefing,
  getBriefingDownloadUrl,
  getBriefingStreamUrl,
  type BriefingResponse,
} from "../../../lib/api";
import { ScorecardPanel } from "./ScorecardPanel";
import { PoRiskPanel } from "./PoRiskPanel";
import { OosPanel } from "./OosPanel";
import { PromoPanel } from "./PromoPanel";
import styles from "./detail.module.css";

type Tab = "narrative" | "scorecard" | "po_risk" | "oos" | "promo";

const TABS: { id: Tab; label: string }[] = [
  { id: "narrative", label: "Narrative" },
  { id: "scorecard", label: "Scorecard" },
  { id: "po_risk", label: "PO Risk" },
  { id: "oos", label: "OOS" },
  { id: "promo", label: "Promo" },
];

function asRecord(value: unknown): Record<string, unknown> {
  if (typeof value === "object" && value !== null) {
    return value as Record<string, unknown>;
  }
  return {};
}

export default function BriefingDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";

  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [streamText, setStreamText] = useState("");
  const [streamDone, setStreamDone] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("narrative");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getBriefing(id)
      .then((payload) => setBriefing(payload))
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load briefing.");
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setStreamText("");
    setStreamDone(false);

    const stream = new EventSource(getBriefingStreamUrl(id));
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string; content?: string };
        if (payload.type === "token" && payload.content) {
          setStreamText((prev) => prev + payload.content);
          return;
        }
        if (payload.type === "done") {
          setStreamDone(true);
          stream.close();
        }
      } catch {
        setStreamDone(true);
        stream.close();
      }
    };

    stream.onerror = () => {
      setStreamDone(true);
      stream.close();
    };

    return () => stream.close();
  }, [id]);

  const request = useMemo(() => asRecord(briefing?.request), [briefing?.request]);
  const fallbackText = typeof briefing?.briefing_text === "string" ? briefing.briefing_text : "";
  const displayText = streamText || fallbackText || "No briefing text available.";

  const scorecard = briefing?.scorecard;
  const benchmarks = briefing?.benchmarks;
  const poRisk = briefing?.po_risk;
  const oos = briefing?.oos_attribution;
  const promo = briefing?.promo_readiness;

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <AppHeader />
        <section className={styles.split}>
          <aside className={styles.panel}>
            <h1 className={styles.heading}>Briefing Detail</h1>
            {loading && <p className={styles.muted}>Loading...</p>}
            {error && <p className={styles.muted}>{error}</p>}
            {!loading && !error && briefing && (
              <>
                <p className={styles.muted}>ID: {briefing.id}</p>
                <div className={styles.list}>
                  <p className={styles.listItem}>Vendor: {String(request.vendor ?? "-")}</p>
                  <p className={styles.listItem}>
                    Meeting Date: {String(request.meeting_date ?? "-")}
                  </p>
                  <p className={styles.listItem}>Status: {String(briefing.status ?? "-")}</p>
                  <p className={styles.listItem}>Stream Replay: {streamDone ? "Done" : "Running"}</p>
                </div>
                <a className={styles.download} href={getBriefingDownloadUrl(id)}>
                  Download .md
                </a>
              </>
            )}
          </aside>

          <article className={styles.panel}>
            <nav className={styles.tabs} aria-label="Briefing sections">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  className={`${styles.tab} ${activeTab === t.id ? styles.tabActive : ""}`}
                  onClick={() => setActiveTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </nav>

            {activeTab === "narrative" && (
              <>
                <p className={styles.muted}>
                  Rendering SSE replay when available, with stored text fallback.
                </p>
                <div className={styles.content}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {displayText}
                  </ReactMarkdown>
                </div>
              </>
            )}

            {activeTab === "scorecard" && (
              <ScorecardPanel scorecard={scorecard} benchmarks={benchmarks} />
            )}

            {activeTab === "po_risk" && (
              <PoRiskPanel data={poRisk} />
            )}

            {activeTab === "oos" && (
              <OosPanel data={oos} />
            )}

            {activeTab === "promo" && (
              <PromoPanel data={promo} />
            )}
          </article>
        </section>
      </div>
    </main>
  );
}
