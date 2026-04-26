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
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                      {row.validation_report && (
                        <span className={styles.badge} style={{ 
                          backgroundColor: row.validation_report.errors?.length > 0 ? "#fee2e2" : (row.validation_report.warnings?.length > 0 ? "#fef3c7" : "#dcfce7"),
                          color: row.validation_report.errors?.length > 0 ? "#991b1b" : (row.validation_report.warnings?.length > 0 ? "#92400e" : "#166534"),
                          borderColor: row.validation_report.errors?.length > 0 ? "#fca5a5" : (row.validation_report.warnings?.length > 0 ? "#fde68a" : "#bbf7d0")
                        }}>
                          {row.validation_report.errors?.length > 0 ? "⚠️ Invalid Data" : (row.validation_report.warnings?.length > 0 ? "⚠️ Data Warnings" : "✅ Valid Data")}
                        </span>
                      )}
                      <span className={styles.badge}>{row.status ?? "unknown"}</span>
                    </div>
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
