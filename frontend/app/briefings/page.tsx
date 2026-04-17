"use client";

import React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "../../components/AppHeader";
import { listBriefings, type BriefingListItem } from "../../lib/api";
import styles from "./list.module.css";

function formatDate(iso: string | undefined): string {
  if (!iso) {
    return "-";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
}

export default function BriefingsPage() {
  const [rows, setRows] = useState<BriefingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listBriefings(100)
      .then((res) => {
        setRows(res.briefings);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load briefing history.");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <AppHeader />
        <section className={styles.panel}>
          <h1 className={styles.heading}>Briefing History</h1>
          <p className={styles.subheading}>
            Latest completed runs from the in-memory API store.
          </p>

          {loading && <p className={styles.empty}>Loading briefings...</p>}
          {error && <p className={styles.empty}>{error}</p>}
          {!loading && !error && rows.length === 0 && (
            <p className={styles.empty}>
              No briefings found yet. <Link href="/briefings/new">Generate your first one</Link>.
            </p>
          )}

          {!loading && !error && rows.length > 0 && (
            <div className={styles.grid}>
              {rows.map((row) => (
                <Link key={row.id} className={styles.card} href={`/briefings/${row.id}`}>
                  <div className={styles.row}>
                    <p className={styles.id}>{row.vendor ?? row.vendor_id ?? "Unknown vendor"}</p>
                    <span className={styles.badge}>{row.status ?? "unknown"}</span>
                  </div>
                  <p className={styles.meta}>
                    Meeting: {row.meeting_date ?? "-"} | Created: {formatDate(row.created_at)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
