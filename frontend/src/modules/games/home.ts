import type { StegeneItem } from "@/components/stegene";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
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
  // A Lecturer in their own test Game is no Student of the Class, so has no name here (6.20).
  if (seat.mine && seat.name == null) return copy.youAlone;
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

/** What the game asks of the Student next (Story 6.5), from the api's `briefing_first` and
 * `status` alone: the briefing until the Starting task is done (also in a game another started),
 * then «Start spillet», then «Gå til Uke n»; `notReady` before the game has its snapshot; null
 * once it is finished. */
export type NextAction = "rules" | "start" | "play" | "notReady" | null;

export function nextAction(game: Pick<StudentGame, "briefing_first" | "status">): NextAction {
  if (game.status === "finished") return null;
  if (game.briefing_first) return "rules";
  if (game.status === "ready") return "start";
  if (game.status === "running") return "play";
  return "notReady";
}

/** «Gå til Uke 11»: the open Week, or Uke 1 while the api has not opened one yet. */
export function toWeekText(game: Pick<StudentGame, "week">): string {
  return nb.games.start.toWeek(game.week ?? 1);
}

/** Hjem's Spillkort (Story 6.17, UX-DR28): `waitsForYou` while the running game waits for this
 * Student's Order (or view, in a Veiledet uke), `ordered` once they have ordered and it waits for
 * others; null with no card: the game does not run, the api sent no `seat_state`, or the briefing
 * still comes first (the pre-play gate leads, with «Les reglene»). From the api's fields alone. */
export type CardState = "waitsForYou" | "ordered";

export function cardState(game: Pick<StudentGame, "status" | "briefing_first" | "seats" | "seat_state">): CardState | null {
  if (game.status !== "running" || game.briefing_first || !game.seat_state) return null;
  const own = game.seats.find((seat) => seat.mine);
  // A Seat an AI player took over has no Spillkort: Hjem says «KI-spiller har bestilt for deg.»
  if (!own || own.taken_over || own.ordered === null || own.ordered === undefined) return null;
  return own.ordered ? "ordered" : "waitsForYou";
}

/** «Netto lager −13 i Uke 11.»: what the Spillkort's hidden mini graph shows at nå, in words. */
export function netSentence(state: NonNullable<StudentGame["seat_state"]>): string {
  return copy.card.net(formatNumber(state.net_inventory), state.week);
}
