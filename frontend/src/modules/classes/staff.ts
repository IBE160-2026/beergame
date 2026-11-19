import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import type { StaffAssistant } from "./api";
import { dayLabel } from "./roster";
import { emailReason } from "./roster-entry";

const copy = nb.classes.staff;

/** An Assistent's status in text (Story 4.9, UX-DR56): «Aktiv», «Invitert, gyldig til og med 3.
 * desember» or «Invitasjonen er utløpt». A Faglærer is always «Aktiv». */
export function assistantStatus(item: StaffAssistant, today: string): string {
  if (item.status === "invited" && item.last_valid_day) return copy.invited(dayLabel(item.last_valid_day, today));
  if (item.status === "expired") return copy.expired;
  return copy.active;
}

/** The line beside the address field for the api's refusal of «Legg til Faglærer» or «Inviter
 * Assistent»; undefined for every other failure, which reads as the form's general line. */
export function staffRefusal(error: unknown): string | undefined {
  if (!(error instanceof ApiRequestError) || error.code !== "invalid_request") return undefined;
  const reason = error.fields.email;
  if (typeof reason !== "string") return undefined;
  if (reason === "not_lecturer") return copy.notLecturer;
  if (reason === "already_staff") return copy.alreadyStaff;
  return emailReason(reason);
}

/** A person as the list and its lines name them: the name with the address, or the address alone
 * for an Invitation not accepted yet. */
export function personLabel(person: { name?: string | null; email: string }): string {
  return person.name ? `${person.name} (${person.email})` : person.email;
}
