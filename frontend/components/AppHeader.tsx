import React from "react";
import Link from "next/link";
import styles from "./app-header.module.css";

export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <p className={styles.title}>Supplier Briefing Agent</p>
        <p className={styles.subtitle}>Phase 5 frontend shell</p>
      </div>
      <nav className={styles.nav}>
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
