import type { StegeneItem } from "@/components/stegene";
import { nb } from "@/copy/nb";
import type { EnrolledSession } from "@/modules/sessions/api";
import { osloDayAndTime } from "@/modules/sessions/dates";
import { roleName } from "@/modules/sessions/sessions";

const copy = nb.homes.student;

type StudentGame = NonNullable<EnrolledSession["game"]>;
type TableSeat = StudentGame["seats"][number];

/** «Spill 17 · Du er Grossist». */
export function gameTitle(game: StudentGame): string {
  return copy.game(game.number, roleName(game.role));
}

/** A Seat's holder in words (FR-22, FR-34, UX-DR69): the Student's name («Sara (deg)» on the
 * own Seat), «KI-spiller» for every AI player, «ledig», or «Ikke lenger i Klassen» for a
 * classmate removed since the start. Never by icon or colour alone. */
export function holderText(seat: TableSeat): string {
  if (seat.holder === "ai") return copy.aiPlayer;
  if (seat.holder === "free") return copy.free;
  const name = seat.name ?? copy.removed;
  return seat.mine ? copy.you(name) : name;
}

/** Stegene's items in words, from the states the api computed (AD-10): the web app decides
 * nothing about which step is open. */
export function stepItems(steps: EnrolledSession["steps"]): StegeneItem[] {
  return (steps ?? []).map(({ step, state }) => ({
    key: step,
    name: copy.stepNames[step],
    state,
    note: state === "current" ? copy.current : state === "done" ? copy.done : copy.locked[step],
  }));
}

const DATE_OF = {
  start: "start_at",
  play: "play_deadline",
  debrief: "debrief_deadline",
  test: "test_deadline",
} as const;

/** «Spillfrist ti. 8. des.»: the next deadline that applies, or null. */
export function deadlineText(session: Pick<EnrolledSession, "next_deadline">): string | null {
  const next = session.next_deadline;
  if (!next) return null;
  return copy.deadline(nb.sessions.dates.names[DATE_OF[next.kind]], osloDayAndTime(next.at).day);
}

/** «to. 26. nov. 14:15, Datalab A2»: an upcoming Lab hour. */
export function labHourText(lab: EnrolledSession["lab_hours"][number]): string {
  const { day, time } = osloDayAndTime(lab.starts_at);
  return copy.labHourItem(day, time, lab.place);
}
