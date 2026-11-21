import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { MessageForm, MessageTo } from "./api";

const copy = nb.messages;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The recipient the page's query names (`?spill=…&student=…`), lower-cased as the api writes ids;
 * null when a given id is not one, which the page refuses like any recipient outside the Class
 * session.
 */
export function recipientFrom(params: { get(name: string): string | null }): MessageTo | null {
  const to: MessageTo = {};
  for (const [name, field] of [
    ["spill", "game"],
    ["student", "student"],
  ] as const) {
    const value = params.get(name);
    if (value === null || value === "") continue;
    if (!ID.test(value)) return null;
    to[field] = value.toLowerCase();
  }
  return to;
}

/** The form's title, which names the recipient: «Melding til Noah, Spill 2». */
export function messageTitle(form: MessageForm): string {
  if (form.kind === "student") {
    return copy.title.student(form.student_name ?? copy.unknownStudent, form.game_id ? (form.game_number ?? null) : null);
  }
  if (form.kind === "class_game") return copy.title.classGame(form.game_number ?? null);
  return copy.title.classSession(form.session_number);
}

/** Whether «Send Melding» may act: some text, someone to send to, no send under way. */
export function canSend(text: string, form: MessageForm, pending: boolean): boolean {
  return text.trim() !== "" && form.students > 0 && !pending;
}

/** The send's own wording of its refusals; every other code reads «Det ble ikke lagret. Prøv
 * igjen.» (`actionErrorMessage`). */
export function sendErrors(form: MessageForm): Record<string, string> {
  return {
    message_too_long: copy.tooLong(formatNumber(form.max_length)),
    message_empty: copy.empty,
    no_recipients: copy.noStudents,
  };
}

/**
 * The client-made key of a send: the same key while the text is the same, so a retry of a send
 * whose answer was lost never sends twice; a new key once the text changed.
 */
export function keyFor(
  previous: { key: string; text: string } | null,
  text: string,
  makeKey: () => string,
): { key: string; text: string } {
  return previous && previous.text === text ? previous : { key: makeKey(), text };
}
