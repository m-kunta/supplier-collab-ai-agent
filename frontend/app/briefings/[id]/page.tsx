"use client";

import React from "react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { AppHeader } from "../../../components/AppHeader";
import {
  getBriefing,
  getBriefingDownloadUrl,
  getBriefingStreamUrl,
  type BriefingResponse
} from "../../../lib/api";
import styles from "./detail.module.css";

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

  useEffect(() => {
    if (!id) {
      return;
    }
    setLoading(true);
    getBriefing(id)
      .then((payload) => {
        setBriefing(payload);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load briefing.");
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) {
      return;
    }

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

    return () => {
      stream.close();
    };
  }, [id]);

  const request = useMemo(() => asRecord(briefing?.request), [briefing?.request]);
  const fallbackText = typeof briefing?.briefing_text === "string" ? briefing.briefing_text : "";
  const displayText = streamText || fallbackText || "No briefing text available.";

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
            <h2 className={styles.heading}>Briefing Text</h2>
            <p className={styles.muted}>
              Rendering SSE replay when available, with stored text fallback.
            </p>
            <pre className={styles.content}>{displayText}</pre>
          </article>
        </section>
      </div>
    </main>
  );
}
