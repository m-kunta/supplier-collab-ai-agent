import React from "react";
import type { ValidationReport } from "../lib/api";
import styles from "./validationBanner.module.css";

export function ValidationBanner({ report }: { report?: ValidationReport }) {
  if (!report) return null;

  const hasErrors = report.errors && report.errors.length > 0;
  const hasWarnings = report.warnings && report.warnings.length > 0;

  if (!hasErrors && !hasWarnings) return null;

  return (
    <div className={`${styles.banner} ${hasErrors ? styles.error : styles.warning}`}>
      <h3 className={styles.title}>
        {hasErrors ? "Dataset Validation Failed" : "Dataset Validation Warnings"}
      </h3>
      {hasErrors && (
        <div className={styles.section}>
          <strong>Errors:</strong>
          <ul>
            {report.errors.map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}
      {hasWarnings && (
        <div className={styles.section}>
          <strong>Warnings:</strong>
          <ul>
            {report.warnings.map((warn, i) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
