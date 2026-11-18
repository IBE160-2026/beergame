import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import type { ListedInvitation, SentInvitation } from "./api";

const copy = nb.admin.users.invitations;

/** «2. des. 2026»: the day an Invitation expires, in Europe/Oslo, with the month words from
 * `nb.ts` whatever the runtime's locale data says. */
export function formatDate(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date(iso));
  const part = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  return `${part("day")}. ${copy.months[part("month") - 1]} ${part("year")}`;
}

/** The status cell: «Åpen», «Akseptert» or «Utløpt». */
export function statusText(invitation: ListedInvitation): string {
  return copy.status[invitation.status];
}

/** Only an Invitation not yet accepted, to an address whose account is not deactivated, can be
 * sent again: the api refuses the others. */
export function canResend(invitation: ListedInvitation): boolean {
  return invitation.status !== "accepted" && !invitation.account_deactivated;
}

/** The date cell: «Akseptert 20. nov. 2026» for an accepted Invitation, whose expiry no longer
 * means anything; else the day its link stops or stopped working. */
export function dateText(invitation: ListedInvitation): string {
  if (invitation.status === "accepted" && invitation.accepted_at) {
    return copy.acceptedOn(formatDate(invitation.accepted_at));
  }
  return formatDate(invitation.expires_at);
}

/** «Send ny invitasjon til kari@example.com»: the button's accessible name. Its visible text is
 * the shorter `resendShort`, so every button in the column has one width. */
export function resendLabel(invitation: ListedInvitation): string {
  return copy.resend(invitation.email);
}

/** «Ny invitasjon sendt til kari@example.com. Den er gyldig i 14 dager.» */
export function resentLine(sent: SentInvitation): string {
  return copy.resent(sent.email, sent.valid_days);
}

/** One row per address and role: a resend replaces the Invitation in it, and the row (with its
 * focused button and its line) stays. */
export function rowKey(invitation: Pick<ListedInvitation, "email" | "role">): string {
  return `${invitation.email}:${invitation.role}`;
}

/** The line for a refused resend: the deactivated account, or the general line (the list reads
 * again, so a row out of date puts itself right). */
export function resendRefusalLine(error: unknown): string {
  if (error instanceof ApiRequestError && error.code === "account_deactivated") return copy.deactivatedAccount;
  return copy.failed;
}

/** The role cell, in the User list's words. */
export function roleText(invitation: ListedInvitation): string {
  return nb.admin.users.list.roles[invitation.role];
}
