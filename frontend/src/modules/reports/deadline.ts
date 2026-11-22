import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { fromOsloInput, osloDateText } from "@/modules/sessions/dates";

const copy = nb.reports.deadline;

/** The block «Frister» on the Studentside (Story 11.13). */
export type StudentDeadlines = components["schemas"]["StudentDeadlinesOut"];

/** The block's idle lines: the Student's Testfrist and Debrieffrist in Europe/Oslo, then
 * «Forlenget. Klassens testfrist: …» or «Som klassen.»; «Klasseøkta har ingen testfrist.» when
 * there is nothing to extend. */
export function deadlineLines(deadlines: StudentDeadlines): string[] {
  if (!deadlines.test_deadline || !deadlines.class_test_deadline) return [copy.noTest];
  const lines = [copy.test(osloDateText(deadlines.test_deadline))];
  if (deadlines.debrief_deadline) lines.push(copy.debrief(osloDateText(deadlines.debrief_deadline)));
  lines.push(deadlines.extended ? copy.extended(osloDateText(deadlines.class_test_deadline)) : copy.asClass);
  return lines;
}

/** Whether the block offers «Forleng testfrist»: the Class session has a Test deadline and the
 * Student has not handed the test in. */
export function canExtend(deadlines: StudentDeadlines): boolean {
  return deadlines.class_test_deadline != null && !deadlines.submitted;
}

/**
 * The new Test deadline as typed (a `datetime-local` value, Europe/Oslo) as the instant the api
 * takes, or the reason it is refused on the field: none chosen, not after the Class session's Test
 * deadline (an extension only ever extends), or not after now. The api judges the same rules again.
 */
export function checkDeadline(local: string, classTestDeadline: string, now: number): { at: string } | { error: string } {
  const at = fromOsloInput(local);
  if (!at) return { error: copy.errors.required };
  if (Date.parse(at) <= Date.parse(classTestDeadline)) {
    return { error: copy.errors.not_later(osloDateText(classTestDeadline)) };
  }
  if (Date.parse(at) <= now) return { error: copy.errors.passed };
  return { at };
}

/** The message on the field for the api's `invalid_extension` reason; undefined for another. */
export function refusalOnField(reason: unknown, classTestDeadline: string): string | undefined {
  if (reason === "not_later") return copy.errors.not_later(osloDateText(classTestDeadline));
  if (reason === "passed") return copy.errors.passed;
  return undefined;
}
