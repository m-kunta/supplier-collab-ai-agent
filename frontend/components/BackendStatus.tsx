"use client";

import React, { useCallback, useEffect, useState } from "react";
import { checkHealth } from "../lib/api";
import styles from "./backend-status.module.css";

type Status = "checking" | "online" | "offline" | "starting";

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  const runCheck = useCallback(async () => {
    const ok = await checkHealth();
    setStatus(ok ? "online" : "offline");
  }, []);

  useEffect(() => {
    runCheck();
    const interval = setInterval(runCheck, 15_000);
    return () => clearInterval(interval);
  }, [runCheck]);

  async function handleStart() {
    setStatus("starting");
    try {
      await fetch("/api/start-backend", { method: "POST" });
    } catch {
      // server route failed — fall through to recheck
    }
    await runCheck();
  }

  if (status === "checking") return null;

  if (status === "online") {
    return (
      <span className={styles.wrap}>
        <span className={`${styles.dot} ${styles.dotOnline}`} />
        <span className={styles.label}>API online</span>
      </span>
    );
  }

  return (
    <span className={styles.wrap}>
      <span className={`${styles.dot} ${styles.dotOffline}`} />
      <span className={styles.label}>API offline</span>
      <button
        className={styles.startBtn}
        onClick={handleStart}
        disabled={status === "starting"}
      >
        {status === "starting" ? "Starting…" : "Start Backend"}
      </button>
    </span>
  );
}
