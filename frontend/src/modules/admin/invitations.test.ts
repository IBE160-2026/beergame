import { describe, expect, it } from "vitest";

import { ApiRequestError } from "@/lib/api/client";

import type { ListedInvitation } from "./api";
import {
  canResend,
  dateText,
  formatDate,
  resendLabel,
  resendRefusalLine,
  resentLine,
  roleText,
  rowKey,
  statusText,
} from "./invitations";

const invitation = (patch: Partial<ListedInvitation> = {}): ListedInvitation => ({
  id: "i1",
  email: "kari@example.com",
  role: "lecturer",
  status: "open",
  expires_at: "2026-12-02T11:01:00Z",
  accepted_at: null,
  account_deactivated: false,
  renewal_requested: false,
  ...patch,
});

describe("the Invitation list's words", () => {
  it("states the expiry day in Oslo time with Norwegian month words", () => {
    expect(formatDate("2026-12-02T11:01:00Z")).toBe("2. des. 2026");
    // 23:30 UTC on 31 December is already New Year's Day in Oslo.
    expect(formatDate("2026-12-31T23:30:00Z")).toBe("1. jan. 2027");
    expect(formatDate("2026-05-17T10:00:00Z")).toBe("17. mai 2026");
  });

  it("names each status", () => {
    expect(statusText(invitation())).toBe("Åpen");
    expect(statusText(invitation({ status: "accepted" }))).toBe("Akseptert");
    expect(statusText(invitation({ status: "expired" }))).toBe("Utløpt");
  });

  it("offers a resend for open and expired Invitations only", () => {
    expect(canResend(invitation())).toBe(true);
    expect(canResend(invitation({ status: "expired" }))).toBe(true);
    expect(canResend(invitation({ status: "accepted" }))).toBe(false);
  });

  it("offers no resend to the address of a deactivated account, which the api refuses", () => {
    expect(canResend(invitation({ status: "expired", account_deactivated: true }))).toBe(false);
    expect(canResend(invitation({ account_deactivated: true }))).toBe(false);
  });

  it("states when an accepted Invitation was accepted instead of its expiry", () => {
    expect(dateText(invitation())).toBe("2. des. 2026");
    expect(dateText(invitation({ status: "accepted", accepted_at: "2026-11-20T09:00:00Z" }))).toBe(
      "Akseptert 20. nov. 2026",
    );
  });

  it("labels the resend with the address and states the result with the real days", () => {
    expect(resendLabel(invitation())).toBe("Send ny invitasjon til kari@example.com");
    const sent = { id: "i2", email: "kari@example.com", role: "lecturer" as const, expires_at: "", valid_days: 14 };
    expect(resentLine(sent)).toBe("Ny invitasjon sendt til kari@example.com. Den er gyldig i 14 dager.");
    expect(resentLine({ ...sent, valid_days: 1 })).toBe("Ny invitasjon sendt til kari@example.com. Den er gyldig i én dag.");
  });

  it("keeps one row per address and role across a resend", () => {
    expect(rowKey(invitation({ id: "i1" }))).toBe(rowKey(invitation({ id: "i2" })));
    expect(rowKey(invitation())).not.toBe(rowKey(invitation({ role: "admin" })));
  });

  it("names the role in the User list's words", () => {
    expect(roleText(invitation())).toBe("Faglærer");
    expect(roleText(invitation({ role: "admin" }))).toBe("Admin");
  });

  it("words a refused resend for a deactivated account, else the general line", () => {
    expect(resendRefusalLine(new ApiRequestError(409, "account_deactivated"))).toBe(
      "Kontoen med denne adressen er deaktivert. Aktiver den før du sender på nytt.",
    );
    expect(resendRefusalLine(new ApiRequestError(409, "invitation_superseded"))).toBe(
      "Invitasjonen ble ikke sendt på nytt. Prøv igjen.",
    );
  });
});
