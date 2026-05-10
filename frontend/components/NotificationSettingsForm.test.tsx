import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { NotificationSettingsForm } from "./NotificationSettingsForm";
import { NotificationSettings } from "../lib/api";

const defaults: NotificationSettings = {
  automation_enabled: true,
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

it("renders automation enabled toggle", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={vi.fn()} saving={false} />);
  expect(screen.getByLabelText(/Enable Automated Pipeline Triggers/i)).toBeInTheDocument();
});

it("renders Slack webhook input", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={vi.fn()} saving={false} />);
  expect(screen.getByLabelText(/slack webhook/i)).toBeInTheDocument();
});

it("renders Teams webhook input", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={vi.fn()} saving={false} />);
  expect(screen.getByLabelText(/teams webhook/i)).toBeInTheDocument();
});

it("toggles email fields when email enabled checkbox is checked", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={vi.fn()} saving={false} />);
  const toggle = screen.getByLabelText(/enable email/i);
  fireEvent.click(toggle);
  expect(screen.getByLabelText(/smtp host/i)).toBeInTheDocument();
});

it("calls onSave with current form values on submit", async () => {
  const onSave = vi.fn();
  render(<NotificationSettingsForm settings={defaults} onSave={onSave} saving={false} />);
  fireEvent.change(screen.getByLabelText(/slack webhook/i), {
    target: { value: "https://hooks.slack.com/T999" },
  });
  fireEvent.submit(screen.getByRole("form"));
  await waitFor(() => expect(onSave).toHaveBeenCalledWith(
    expect.objectContaining({ slack_webhook_url: "https://hooks.slack.com/T999" })
  ));
});

it("shows saving state on button when saving=true", () => {
  render(<NotificationSettingsForm settings={defaults} onSave={vi.fn()} saving={true} />);
  expect(screen.getByRole("button", { name: /saving/i })).toBeDisabled();
});
