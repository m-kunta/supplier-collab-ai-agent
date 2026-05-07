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
