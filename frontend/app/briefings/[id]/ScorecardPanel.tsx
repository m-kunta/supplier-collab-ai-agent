import React from "react";
import type { ScorecardMetric, BenchmarkMetric } from "../../../lib/api";
import styles from "./panels.module.css";

const METRIC_LABELS: Record<string, string> = {
  FILL_RATE: "Fill Rate",
  OTIF: "OTIF",
  FORECAST_ACCURACY: "Forecast Accuracy",
  LEAD_TIME_COMPLIANCE: "Lead Time Compliance",
  PROMO_FILL_RATE: "Promo Fill Rate",
};

function label(key: string): string {
  return METRIC_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function delta(v: number): string {
  const pp = (v * 100).toFixed(1);
  return v >= 0 ? `+${pp}pp` : `${pp}pp`;
}

function directionClass(d: ScorecardMetric["trend_direction"]): string {
  if (d === "improving") return styles.improving;
  if (d === "declining") return styles.declining;
  return styles.stable;
}

function directionArrow(d: ScorecardMetric["trend_direction"]): string {
  if (d === "improving") return "↑";
  if (d === "declining") return "↓";
  return "→";
}

interface Props {
  scorecard?: Record<string, ScorecardMetric>;
  benchmarks?: Record<string, BenchmarkMetric>;
}

export function ScorecardPanel({ scorecard, benchmarks }: Props) {
  if (!scorecard || Object.keys(scorecard).length === 0) {
    return <p className={styles.noData}>No scorecard data available.</p>;
  }

  const hasBenchmarks = !!benchmarks && Object.keys(benchmarks).length > 0;

  return (
    <div>
      <table className={styles.table}>
        <thead>
          <tr>
            <th className={styles.th}>Metric</th>
            <th className={styles.th}>Current</th>
            <th className={styles.th}>4w Δ</th>
            <th className={styles.th}>13w Δ</th>
            <th className={styles.th}>Trend</th>
            {hasBenchmarks && <th className={styles.th}>Peer Avg</th>}
            {hasBenchmarks && <th className={styles.th}>Best-in-Class</th>}
            {hasBenchmarks && <th className={styles.th}>Gap to BIC</th>}
          </tr>
        </thead>
        <tbody>
          {Object.entries(scorecard).map(([key, m]) => {
            const bm = benchmarks?.[key];
            return (
              <tr key={key}>
                <td className={styles.td}>{label(key)}</td>
                <td className={styles.td}>{pct(m.current_value)}</td>
                <td className={`${styles.td} ${directionClass(m.trend_direction)}`}>
                  {delta(m.trend_4w)}
                </td>
                <td className={`${styles.td} ${directionClass(m.trend_direction)}`}>
                  {delta(m.trend_13w)}
                </td>
                <td className={`${styles.td} ${directionClass(m.trend_direction)}`}>
                  {directionArrow(m.trend_direction)} {m.trend_direction}
                </td>
                {hasBenchmarks && (
                  <td className={styles.td}>{bm ? pct(bm.peer_avg) : "—"}</td>
                )}
                {hasBenchmarks && (
                  <td className={styles.td}>{bm ? pct(bm.best_in_class) : "—"}</td>
                )}
                {hasBenchmarks && (
                  <td className={`${styles.td} ${bm && bm.gap_to_bic < 0 ? styles.declining : ""}`}>
                    {bm ? delta(bm.gap_to_bic) : "—"}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
