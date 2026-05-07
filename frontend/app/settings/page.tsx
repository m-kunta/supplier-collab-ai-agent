"use client";

import React, { useEffect, useState } from "react";
import {
  getSettings,
  updateSettings,
  getSchedule,
  NotificationSettings,
  ScheduledJob,
} from "../../lib/api";
import { NotificationSettingsForm } from "../../components/NotificationSettingsForm";

export default function SettingsPage() {
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings().then(setSettings).catch((e: Error) => setError(e.message));
    getSchedule().then((r) => setJobs(r.jobs)).catch(() => {});
  }, []);

  const handleSave = async (updated: NotificationSettings) => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const result = await updateSettings(updated);
      setSettings(result);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main style={{ maxWidth: 640, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Notification Settings</h1>
      <p style={{ color: "#888", fontSize: "0.875rem" }}>
        ⚠️ Prototype — configuration is stored in{" "}
        <code>config/notification_settings.json</code>.
      </p>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", padding: "0.75rem", borderRadius: 6, marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {saved && (
        <div style={{ background: "#f0fdf4", border: "1px solid #86efac", padding: "0.75rem", borderRadius: 6, marginBottom: "1rem" }}>
          Settings saved.
        </div>
      )}

      {settings ? (
        <NotificationSettingsForm settings={settings} onSave={handleSave} saving={saving} />
      ) : (
        !error && <p>Loading…</p>
      )}

      <hr style={{ margin: "2rem 0" }} />

      <h2>Scheduled Jobs</h2>
      {jobs.length === 0 ? (
        <p style={{ color: "#888" }}>No scheduled jobs currently queued.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "1px solid #e5e7eb" }}>Job</th>
              <th style={{ textAlign: "left", padding: "0.5rem", borderBottom: "1px solid #e5e7eb" }}>Next Run</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td style={{ padding: "0.5rem" }}>{job.name}</td>
                <td style={{ padding: "0.5rem", color: "#888" }}>
                  {job.next_run ? new Date(job.next_run).toLocaleString() : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
