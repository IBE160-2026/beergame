import { nb } from "@/copy/nb";

import type { MessageTo, MyMessage, SentMessage } from "./api";

const copy = nb.messages;

/** «Til Noah, Spill 2»: whom a sent Message went to, as «Meldinger» lists it (Story 7.10). */
export function recipientLine(item: SentMessage, sessionNumber: number): string {
  switch (item.kind) {
    case "student":
      return item.student_name === null
        ? copy.sentList.to.formerStudent
        : copy.sentList.to.student(item.student_name, item.game_id ? (item.game_number ?? null) : null);
    case "class_game":
      return copy.sentList.to.classGame(item.game_number ?? null);
    case "class_session":
      return copy.sentList.to.classSession(sessionNumber);
    default:
      return copy.sentList.to.list(item.students);
  }
}

/** The Meldingsskjema for the same recipient, or null where there is none to write to again: a
 * list a calling module named, or a Student no longer in the Class. */
export function againTo(item: SentMessage): MessageTo | null {
  switch (item.kind) {
    case "student":
      if (item.student_id === null || item.student_name === null) return null;
      return item.game_id ? { game: item.game_id, student: item.student_id } : { student: item.student_id };
    case "class_game":
      return item.game_id ? { game: item.game_id } : null;
    case "class_session":
      return {};
    default:
      return null;
  }
}

/** The sender as shown, or «Faglærer» when the account is gone. */
export function senderName(item: Pick<MyMessage, "sender_name">): string {
  return item.sender_name ?? copy.mine.unknownSender;
}

/**
 * What the Hjem live region says when Messages arrive (Story 7.10, AD-8): the Messages in `items`
 * whose id was not in the answer before (`seen`), as «Ny melding fra Bård.» or «Nye meldinger: 2.»;
 * null when nothing is new or there was no answer before (the page just opened).
 */
export function arrivalText(seen: ReadonlySet<string> | null, items: readonly MyMessage[]): string | null {
  if (seen === null) return null;
  const fresh = items.filter((item) => !seen.has(item.id));
  if (fresh.length === 0) return null;
  return copy.mine.arrived(senderName(fresh[0]!), fresh.length);
}
