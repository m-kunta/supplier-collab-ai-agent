import React from "react";
import type {
  InventoryInsights,
  ForecastInsights,
  AsnInsights,
  ChargebackInsights,
  TradeFundInsights,
} from "../../../lib/api";
import styles from "./panels.module.css";

interface Props {
  inventory?: InventoryInsights;
  forecast?: ForecastInsights;
  asn?: AsnInsights;
  chargebacks?: ChargebackInsights;
  tradeFunds?: TradeFundInsights;
}

function pct(value: number | null | undefined): string {
  if (typeof value !== "number") return "-";
  return `${Math.round(value * 100)}%`;
}

export function Phase8InsightsPanel({
  inventory,
  forecast,
  asn,
  chargebacks,
  tradeFunds,
}: Props) {
  if (!inventory && !forecast && !asn && !chargebacks && !tradeFunds) {
    return <p className={styles.noData}>No Phase 8 insight data available.</p>;
  }

  return (
    <div>
      <div className={styles.section}>
        <p className={styles.sectionTitle}>Supply-Side Insights</p>
        <div className={styles.summaryRow}>
          {inventory && (
            <div className={styles.statCard}>
              <div className={`${styles.statValue} ${inventory.low_days_of_supply_sku_count > 0 ? styles.declining : styles.stable}`}>
                {inventory.low_days_of_supply_sku_count}
              </div>
              <div className={styles.statLabel}>Low DOS SKUs</div>
            </div>
          )}
          {forecast && (
            <div className={styles.statCard}>
              <div className={styles.statValue}>{pct(forecast.avg_forecast_accuracy_pct)}</div>
              <div className={styles.statLabel}>Forecast Accuracy</div>
            </div>
          )}
          {asn && (
            <div className={styles.statCard}>
              <div className={`${styles.statValue} ${asn.overdue_shipment_count > 0 ? styles.declining : styles.stable}`}>
                {asn.overdue_shipment_count}
              </div>
              <div className={styles.statLabel}>Overdue ASNs</div>
            </div>
          )}
        </div>
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Commercial Insights</p>
        <div className={styles.summaryRow}>
          {chargebacks && (
            <div className={styles.statCard}>
              <div className={`${styles.statValue} ${chargebacks.total_chargeback_amount > 0 ? styles.declining : styles.stable}`}>
                ${Math.round(chargebacks.total_chargeback_amount)}
              </div>
              <div className={styles.statLabel}>Chargebacks</div>
            </div>
          )}
          {tradeFunds && (
            <div className={styles.statCard}>
              <div className={styles.statValue}>{pct(tradeFunds.spend_compliance_pct)}</div>
              <div className={styles.statLabel}>Trade Fund Compliance</div>
            </div>
          )}
        </div>
      </div>

      <div className={styles.sectionGrid}>
        {inventory && inventory.low_days_of_supply_skus.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Low Cover SKUs</p>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>SKU</th>
                  <th className={styles.th}>Days of Supply</th>
                </tr>
              </thead>
              <tbody>
                {inventory.low_days_of_supply_skus.map((item) => (
                  <tr key={item.sku}>
                    <td className={styles.td}>{item.sku}</td>
                    <td className={styles.td}>
                      <span className={`${styles.badge} ${item.days_of_supply !== null && item.days_of_supply < 7 ? styles.red : styles.yellow}`}>
                        {item.days_of_supply ?? "-"} days
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {forecast && forecast.largest_underforecast_skus.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Largest Underforecast SKUs</p>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>SKU</th>
                  <th className={styles.th}>Shortfall</th>
                </tr>
              </thead>
              <tbody>
                {forecast.largest_underforecast_skus.map((item) => {
                  const maxShortfall = Math.max(...forecast.largest_underforecast_skus.map(f => f.shortfall_qty));
                  const pct = maxShortfall > 0 ? (item.shortfall_qty / maxShortfall) * 100 : 0;
                  return (
                    <tr key={item.sku}>
                      <td className={styles.td}>{item.sku}</td>
                      <td className={styles.td}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={styles.declining}>{item.shortfall_qty}</span>
                          <div className={styles.barWrap} style={{ width: '60px', margin: 0, height: '6px' }}>
                            <div className={styles.barFill} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {asn && asn.top_overdue_asns.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Overdue ASN Lines</p>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>ASN</th>
                  <th className={styles.th}>Days Overdue</th>
                </tr>
              </thead>
              <tbody>
                {asn.top_overdue_asns.map((item) => (
                  <tr key={item.asn_number}>
                    <td className={styles.td}>{item.asn_number}</td>
                    <td className={styles.td}>
                      <span className={`${styles.badge} ${item.days_overdue > 7 ? styles.red : styles.yellow}`}>
                        {item.days_overdue} days
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {chargebacks && chargebacks.top_chargeback_types.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>Top Chargeback Types</p>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>Type</th>
                  <th className={styles.th}>Count</th>
                  <th className={styles.th}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {chargebacks.top_chargeback_types.map((item) => {
                  const maxChargeback = Math.max(...chargebacks.top_chargeback_types.map(c => c.amount));
                  const pct = maxChargeback > 0 ? (item.amount / maxChargeback) * 100 : 0;
                  return (
                    <tr key={item.chargeback_type}>
                      <td className={styles.td}>{item.chargeback_type}</td>
                      <td className={styles.td}>{item.count}</td>
                      <td className={styles.td}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={styles.declining}>${Math.round(item.amount)}</span>
                          <div className={styles.barWrap} style={{ width: '60px', margin: 0, height: '6px' }}>
                            <div className={styles.barFill} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {tradeFunds && tradeFunds.at_risk_funds.length > 0 && (
          <div className={styles.section}>
            <p className={styles.sectionTitle}>At-Risk Trade Funds</p>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>Fund</th>
                  <th className={styles.th}>Committed</th>
                  <th className={styles.th}>Spend</th>
                </tr>
              </thead>
              <tbody>
                {tradeFunds.at_risk_funds.map((item) => {
                  const spendPct = item.committed_amount > 0 ? Math.min(100, (item.actual_spend / item.committed_amount) * 100) : 0;
                  return (
                    <tr key={item.fund_id}>
                      <td className={styles.td}>{item.fund_id}</td>
                      <td className={styles.td}>${Math.round(item.committed_amount)}</td>
                      <td className={styles.td}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className={styles.declining}>${Math.round(item.actual_spend)}</span>
                          <div className={styles.barWrap} style={{ width: '60px', margin: 0, height: '6px' }}>
                            <div className={styles.barFill} style={{ width: `${spendPct}%`, background: '#ffc846' }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
