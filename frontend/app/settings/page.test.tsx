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
