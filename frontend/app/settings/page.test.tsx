import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import SettingsPage from "./page";
import * as api from "../../lib/api";

vi.mock("../../lib/api");

const mockSettings: api.NotificationSettings = {
  slack_webhook_url: "",
  teams_webhook_url: "",
  email_enabled: false,
  email_smtp_host: "",
  email_smtp_port: 587,
  email_smtp_user: "",
  email_smtp_password: "",
  email_from: "",
  email_to: [],
};

beforeEach(() => {
  vi.mocked(api.getSettings).mockResolvedValue(mockSettings);
  vi.mocked(api.updateSettings).mockResolvedValue(mockSettings);
  vi.mocked(api.getSchedule).mockResolvedValue({ jobs: [] });
  vi.mocked(api.getDeliveryAttempts).mockResolvedValue({ attempts: [], total: 0 });
});

it("renders page heading", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/notification settings/i)).toBeInTheDocument());
});

it("renders schedule section with a job", async () => {
  vi.mocked(api.getSchedule).mockResolvedValue({
    jobs: [{ id: "poll_calendar", name: "Poll Google Calendar", next_run: "2026-05-08T10:00:00Z" }],
  });
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/poll google calendar/i)).toBeInTheDocument());
});

it("shows no scheduled jobs message when list is empty", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/no scheduled jobs/i)).toBeInTheDocument());
});

it("renders recent delivery attempts", async () => {
  vi.mocked(api.getDeliveryAttempts).mockResolvedValue({
    attempts: [{
      id: "attempt-1",
      briefing_id: "brief-123",
      channel: "slack",
      status: "dead_letter",
      attempt_count: 3,
      payload: { vendor: "Northstar Foods Co" },
      last_error: "timeout",
      created_at: "2026-05-29T00:00:00Z",
      updated_at: "2026-05-29T00:01:00Z"
    }],
    total: 1
  });

  render(<SettingsPage />);

  await waitFor(() => expect(screen.getByText(/recent delivery attempts/i)).toBeInTheDocument());
  expect(screen.getByText("dead_letter")).toBeInTheDocument();
  expect(screen.getByText("slack")).toBeInTheDocument();
  expect(screen.getByText("brief-123")).toBeInTheDocument();
  expect(screen.getByText("timeout")).toBeInTheDocument();
});

it("shows no delivery attempts message when list is empty", async () => {
  render(<SettingsPage />);
  await waitFor(() => expect(screen.getByText(/no delivery attempts recorded yet/i)).toBeInTheDocument());
});
