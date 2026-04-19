import React from "react";
import type { PoRiskData } from "../../../lib/api";
import styles from "./panels.module.css";

function tierClass(tier: string): string {
  if (tier === "red") return styles.red;
  if (tier === "yellow") return styles.yellow;
  return styles.green;
}

interface Props {
  data?: PoRiskData;
}

export function PoRiskPanel({ data }: Props) {
  if (!data) {
    return <p className={styles.noData}>No PO risk data available.</p>;
  }

  const { summary, line_items } = data;

  return (
    <div>
      <div className={styles.summaryRow}>
        <div className={styles.statCard}>
          <div className={`${styles.statValue} ${styles.red}`}>{summary.red}</div>
          <div className={styles.statLabel}>Red</div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statValue} ${styles.yellow}`}>{summary.yellow}</div>
          <div className={styles.statLabel}>Yellow</div>
        </div>
        <div className={styles.statCard}>
          <div className={`${styles.statValue} ${styles.green}`}>{summary.green}</div>
          <div className={styles.statLabel}>Green</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{summary.total}</div>
          <div className={styles.statLabel}>Total POs</div>
        </div>
      </div>

      {line_items.length === 0 ? (
        <p className={styles.noData}>No PO line items.</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>PO #</th>
              <th className={styles.th}>Line</th>
              <th className={styles.th}>SKU</th>
              <th className={styles.th}>Requested Delivery</th>
              <th className={styles.th}>Status</th>
              <th className={styles.th}>Days Late</th>
              <th className={styles.th}>Tier</th>
            </tr>
          </thead>
          <tbody>
            {line_items.map((item, i) => (
              <tr key={`${item.po_number}-${item.po_line}-${i}`}>
                <td className={styles.td}>{item.po_number}</td>
                <td className={styles.td}>{item.po_line}</td>
                <td className={styles.td}>{item.sku}</td>
                <td className={styles.td}>{item.requested_delivery_date}</td>
                <td className={styles.td} style={{ textTransform: "capitalize" }}>{item.po_status}</td>
                <td className={`${styles.td} ${item.days_late > 0 ? styles.declining : styles.stable}`}>
                  {item.days_late > 0 ? `+${item.days_late}d` : `${item.days_late}d`}
                </td>
                <td className={styles.td}>
                  <span className={`${styles.badge} ${tierClass(item.risk_tier)}`}>
                    {item.risk_tier}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
