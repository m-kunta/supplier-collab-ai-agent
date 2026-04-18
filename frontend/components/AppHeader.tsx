import React from "react";
import Link from "next/link";
import { BackendStatus } from "./BackendStatus";
import styles from "./app-header.module.css";

export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <p className={styles.title}>Supplier Briefing Agent</p>
        <p className={styles.subtitle}>Pre-meeting intelligence</p>
      </div>
      <nav className={styles.nav}>
        <BackendStatus />
        <Link href="/briefings/new" className={styles.link}>
          New Briefing
        </Link>
        <Link href="/briefings" className={styles.link}>
          Briefing History
        </Link>
      </nav>
    </header>
  );
}
