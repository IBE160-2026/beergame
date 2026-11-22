import { nb } from "@/copy/nb";
import { osloDateText } from "@/modules/sessions/dates";

import type { MyTest, MyTestItem } from "./api";

const copy = nb.tests.individual;

/** Where the Individual test page stands, from the api's answer or refusal alone (AD-10). */
export type TestView = "statement" | "open" | "closed" | "submitted" | "auto_submitted" | "locked" | "denied" | "other";

export function testView(data: MyTest | undefined, code: string | null): TestView {
  if (data) return data.state;
  if (code === "replay_required") return "locked";
  if (code === "forbidden") return "denied";
  return "other";
}

/** «Testfrist to. 18. des. kl. 23:59.», or null when the Class session has none. */
export function deadlineLine(test: Pick<MyTest, "test_deadline">): string | null {
  return test.test_deadline ? copy.deadline(osloDateText(test.test_deadline)) : null;
}

/** An item's heading and its type in words: «Oppgave 3», «Langsvar». */
export function itemLines(item: Pick<MyTestItem, "number" | "type">): { heading: string; type: string } {
  return { heading: copy.item(item.number), type: copy.types[item.type] };
}

/**
 * A long-answer or Adapted item's label (Story 11.8, FR-34, UX-DR69): an Adapted item whose
 * wording an LLM chose reads «KI-generert, kan ta feil: «…»» and is marked `ai`, with the note
 * that the numbers are the code's; every other item reads its question as written. Only
 * `wording.ai_generated` decides; the web app never guesses.
 */
export function itemLabel(item: Pick<MyTestItem, "title" | "wording">): { label: string; ai: boolean; note: string | null } {
  if (item.wording?.ai_generated) {
    return { label: nb.debrief.aiText(item.wording.text), ai: true, note: nb.debrief.aiNote };
  }
  return { label: item.title, ai: false, note: null };
}

/**
 * Whether an item has an answer to hand in (Story 11.10, the review before «Lever testen»): a
 * stored value that is not null, not blank text and not a table with every cell empty. Display
 * only: it lists the items to look at again, and the api judges and scores what is handed in.
 */
export function isAnswered(item: Pick<MyTestItem, "answer">): boolean {
  const value: unknown = item.answer?.value ?? null;
  if (value === null) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.some((cell) => cell !== null);
  return true;
}

/** The numbers of the items not answered, in order: «4, 7 og 9». */
export function unansweredNumbers(test: Pick<MyTest, "items">): number[] {
  return test.items.filter((item) => !isAnswered(item)).map((item) => item.number);
}

/** What goes before the `index`th of `count` numbers in «4, 7 og 9»: nothing, «, » or « og ». */
export function listSeparator(index: number, count: number): string {
  if (index === 0) return "";
  return index === count - 1 ? copy.submit.listAnd : copy.submit.listComma;
}

/** The id of an item's place on the page, the target of its link in the review. */
export function itemAnchor(number: number): string {
  return `oppgave-${number}`;
}

/** «Levert to. 18. des. kl. 21:40. Du kan ikke endre svarene.», or the auto-submitted line. */
export function submittedLine(test: Pick<MyTest, "state" | "submitted_at">): string | null {
  if (test.state === "auto_submitted") return copy.submit.autoSubmitted;
  if (test.state !== "submitted" || !test.submitted_at) return null;
  return copy.submit.submitted(osloDateText(test.submitted_at));
}
