import { nb } from "@/copy/nb";

import type { Registration, Registrations, RegistrationStatus } from "./api";
import { dayLabel } from "./roster";

const copy = nb.classes.registration;

/** The statuses in the filter, in the order an Invitation travels (Story 4.7, FR-9). */
export const STATUSES = [
  "not_invited",
  "invited",
  "renewal_requested",
  "bounced",
  "unregistered",
  "registered",
  "registered_manually",
] as const satisfies readonly RegistrationStatus[];

/** One address's status in text (NFR-10): «Invitert, gyldig til og med 3. desember», «Kom ikke
 * fram, permanent feil», «Ba om ny Invitasjon» … (`today` is an ISO date on the browser's
 * clock, for the year). */
export function statusLabel(item: Registration, today: string): string {
  if (item.status === "invited" && item.last_valid_day) {
    return copy.invitedUntil(dayLabel(item.last_valid_day, today));
  }
  if (item.status === "bounced" && item.bounce_class) {
    return nb.classes.invitations.bounceStatus(item.bounce_class);
  }
  return copy.status[item.status];
}

/** «Teststudent · Samtykket» for a test student of a Control test (Story 12.8, UX-DR57); null
 * for anyone else. */
export function testStudentLabel(item: Registration): string | null {
  if (!item.test_student) return null;
  const consent = item.consent ? copy.consent[item.consent] : null;
  return consent ? `${copy.testStudent} · ${consent}` : copy.testStudent;
}

/** The addresses with `status` (all for null) whose address contains `query`, trimmed and
 * ignoring case. */
export function filterRegistrations(
  items: readonly Registration[],
  status: RegistrationStatus | null,
  query: string,
): Registration[] {
  const needle = query.trim().toLowerCase();
  return items.filter((item) => (status === null || item.status === status) && item.email.includes(needle));
}

/** The three parts of the bar, as shares of the Roster that add up to 1 (none when it is empty). */
export function barShares(totals: Registrations["totals"]): { registered: number; manual: number; unregistered: number } {
  const all = totals.registered + totals.registered_manually + totals.unregistered;
  if (all === 0) return { registered: 0, manual: 0, unregistered: 0 };
  return {
    registered: totals.registered / all,
    manual: totals.registered_manually / all,
    unregistered: totals.unregistered / all,
  };
}

/** How many a reminder to all would reach, and how many it leaves out for a hard bounce. */
export function reminderReach(items: readonly Registration[]): { reach: number; leftOut: number } {
  const waiting = items.filter((i) => i.status !== "registered" && i.status !== "registered_manually");
  const reach = waiting.filter((i) => i.remindable).length;
  return { reach, leftOut: waiting.length - reach };
}
