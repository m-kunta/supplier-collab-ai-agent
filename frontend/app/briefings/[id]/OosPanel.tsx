import React from "react";
import type { OosAttribution } from "../../../lib/api";
import styles from "./panels.module.css";

interface Props {
  data?: OosAttribution;
}

export function OosPanel({ data }: Props) {
  if (!data) {
    return <p className={styles.noData}>No OOS attribution data available.</p>;
  }

  const vcPct = Math.round(data.vendor_controllable_pct * 100);
  const ddPct = data.total_oos_events > 0
    ? Math.round((data.demand_driven / data.total_oos_events) * 100)
    : 0;
  const uaPct = data.total_oos_events > 0
    ? Math.round((data.unattributed / data.total_oos_events) * 100)
    : 0;

  return (
    <div>
      <div className={styles.summaryRow}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{data.total_oos_events}</div>
          <div className={styles.statLabel}>OOS Events</div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statValue} ${vcPct > 50 ? styles.declining : ""}`}>
            {vcPct}%
          </div>
          <div className={styles.statLabel}>Vendor Ctrl.</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{data.total_units_lost.toLocaleString()}</div>
          <div className={styles.statLabel}>Units Lost</div>
        </div>
        {data.recurring_skus.length > 0 && (
          <div className={styles.statCard}>
            <div className={`${styles.statValue} ${styles.declining}`}>{data.recurring_skus.length}</div>
            <div className={styles.statLabel}>Recurring SKUs</div>
          </div>
        )}
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Attribution Split</p>
        <div className={styles.barWrap}>
          <div className={styles.barFill} style={{ width: `${vcPct}%` }} />
        </div>
        <div className={styles.barLegend}>
          <span className={styles.declining}>■ Vendor controllable {vcPct}%</span>
          <span>■ Demand driven {ddPct}%</span>
          {data.unattributed > 0 && <span>■ Unattributed {uaPct}%</span>}
        </div>
      </div>

      {data.top_skus.length > 0 && (
        <div className={styles.section}>
          <p className={styles.sectionTitle}>Top OOS SKUs</p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.th}>SKU</th>
                <th className={styles.th}>Events</th>
                <th className={styles.th}>Primary Cause</th>
                <th className={styles.th}>Recurring</th>
              </tr>
            </thead>
            <tbody>
              {data.top_skus.map((sku) => (
                <tr key={sku.sku}>
                  <td className={styles.td}>{sku.sku}</td>
                  <td className={styles.td}>{sku.oos_count}</td>
                  <td className={`${styles.td} ${sku.primary_cause === "vendor_controllable" ? styles.declining : styles.stable}`}>
                    {sku.primary_cause.replace(/_/g, " ")}
                  </td>
                  <td className={styles.td}>
                    {sku.is_recurring
                      ? <span className={styles.declining}>Yes</span>
                      : <span className={styles.stable}>No</span>}
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
