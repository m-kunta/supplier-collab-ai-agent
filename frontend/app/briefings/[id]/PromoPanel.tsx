import React from "react";
import type { PromoReadiness } from "../../../lib/api";
import styles from "./panels.module.css";

function tierClass(tier: string): string {
  if (tier === "red") return styles.red;
  if (tier === "yellow") return styles.yellow;
  return styles.green;
}

function scoreTier(score: number): string {
  if (score >= 0.7) return "green";
  if (score >= 0.4) return "yellow";
  return "red";
}

interface Props {
  data?: PromoReadiness;
}

export function PromoPanel({ data }: Props) {
  if (!data) {
    return <p className={styles.noData}>No promo readiness data available.</p>;
  }

  const scorePct = Math.round(data.overall_score * 100);

  return (
    <div>
      <div className={styles.scoreHero}>
        <div className={`${styles.scoreNumber} ${tierClass(data.risk_tier)}`}>
          {scorePct}%
        </div>
        <div className={styles.scoreMeta}>
          <span className={`${styles.badge} ${tierClass(data.risk_tier)}`}>
            {data.risk_tier} risk
          </span>
          <span style={{ fontSize: "0.78rem", color: "var(--color-text-muted)" }}>
            Overall readiness
          </span>
        </div>
      </div>

      {data.events.length === 0 ? (
        <p className={styles.noData}>No promo events found.</p>
      ) : (
        <div className={styles.section}>
          <p className={styles.sectionTitle}>Promo Events</p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>Event</th>
                <th className={styles.th}>Start Date</th>
                <th className={styles.th}>Readiness Score</th>
                <th className={styles.th}>PO Coverage</th>
              </tr>
            </thead>
            <tbody>
              {data.events.map((ev) => (
                <tr key={ev.promo_id}>
                  <td className={styles.td}>{ev.event_name}</td>
                  <td className={styles.td}>{ev.start_date}</td>
                  <td className={`${styles.td} ${tierClass(scoreTier(ev.score))}`}>
                    {Math.round(ev.score * 100)}%
                  </td>
                  <td className={styles.td}>
                    {ev.covered_by_po
                      ? <span className={styles.covered}>✓ Covered</span>
                      : <span className={styles.notCovered}>✗ Not covered</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
