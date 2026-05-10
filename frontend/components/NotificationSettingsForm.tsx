"use client";

import React, { useState } from "react";
import { NotificationSettings } from "../lib/api";

interface Props {
  settings: NotificationSettings;
  onSave: (settings: NotificationSettings) => void;
  saving: boolean;
}

export function NotificationSettingsForm({ settings, onSave, saving }: Props) {
  const [form, setForm] = useState<NotificationSettings>(settings);

  const set = (key: keyof NotificationSettings, value: unknown) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} aria-label="notification settings">
      <section style={{ marginBottom: "2rem", padding: "1rem", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8 }}>
        <label style={{ display: "flex", alignItems: "center", fontWeight: "bold", fontSize: "1.1rem" }}>
          <input
            id="automation_enabled"
            type="checkbox"
            checked={form.automation_enabled}
            onChange={(e) => set("automation_enabled", e.target.checked)}
            style={{ marginRight: "0.75rem", width: 18, height: 18 }}
          />
          Enable Automated Pipeline Triggers
        </label>
        <p style={{ margin: "0.5rem 0 0 2rem", color: "#64748b", fontSize: "0.9rem" }}>
          When enabled, the system will automatically generate briefings 24 and 2 hours before scheduled meetings.
        </p>
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>Slack</h3>
        <label htmlFor="slack_webhook_url">Slack Webhook URL</label>
        <input
          id="slack_webhook_url"
          type="url"
          placeholder="https://hooks.slack.com/services/..."
          value={form.slack_webhook_url}
          onChange={(e) => set("slack_webhook_url", e.target.value)}
          style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
        />
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>Microsoft Teams</h3>
        <label htmlFor="teams_webhook_url">Teams Webhook URL</label>
        <input
          id="teams_webhook_url"
          type="url"
          placeholder="https://outlook.office.com/webhook/..."
          value={form.teams_webhook_url}
          onChange={(e) => set("teams_webhook_url", e.target.value)}
          style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
        />
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h3>Email</h3>
        <label>
          <input
            id="email_enabled"
            type="checkbox"
            checked={form.email_enabled}
            onChange={(e) => set("email_enabled", e.target.checked)}
          />{" "}
          Enable Email notifications
        </label>

        {form.email_enabled && (
          <div style={{ marginTop: "1rem", display: "grid", gap: "0.75rem" }}>
            <div>
              <label htmlFor="email_smtp_host">SMTP Host</label>
              <input
                id="email_smtp_host"
                type="text"
                value={form.email_smtp_host}
                onChange={(e) => set("email_smtp_host", e.target.value)}
                style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
              />
            </div>
            <div>
              <label htmlFor="email_from">From Address</label>
              <input
                id="email_from"
                type="email"
                value={form.email_from}
                onChange={(e) => set("email_from", e.target.value)}
                style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
              />
            </div>
            <div>
              <label htmlFor="email_to">To Addresses (comma-separated)</label>
              <input
                id="email_to"
                type="text"
                value={form.email_to.join(", ")}
                onChange={(e) =>
                  set("email_to", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
                }
                style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
              />
            </div>
          </div>
        )}
      </section>

      <button type="submit" disabled={saving}>
        {saving ? "Saving…" : "Save Settings"}
      </button>
    </form>
  );
}
