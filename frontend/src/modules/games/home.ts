import type { StegeneItem } from "@/components/stegene";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { DEBRIEF_PATH, TEST_PATH } from "@/modules/identity/homes";
import type { EnrolledSession } from "@/modules/sessions/api";
import { osloDayAndTime } from "@/modules/sessions/dates";
import { roleName } from "@/modules/sessions/sessions";

const copy = nb.homes.student;

type StudentGame = NonNullable<EnrolledSession["game"]>;
type TableSeat = StudentGame["seats"][number];

type Titled = Pick<StudentGame, "number" | "role" | "replay" | "test_game"> & { makeup?: boolean };

/** «Spill 17 · Du er Grossist»; «Replay · Du er Grossist» for the Replay (Story 10.4);
 * «Oppfølgingsspill · Du er Grossist» for the Oppfølgingsspill (Story 13.4). */
export function gameTitle(game: Titled): string {
  if (game.makeup) return copy.makeup.title(roleName(game.role));
  return game.replay ? copy.replay.title(roleName(game.role)) : copy.game(game.number, roleName(game.role));
}

/** «Grossist, Spill 17» under the Uke on the play screen; «Grossist, Replay» for the Replay;
 * «Grossist, Oppfølgingsspill» for the Oppfølgingsspill. */
export function roleGameText(game: Titled): string {
  if (game.makeup) return nb.games.play.roleMakeup(roleName(game.role));
  return game.replay ? nb.games.play.roleReplay(roleName(game.role)) : nb.games.play.roleGame(roleName(game.role), game.number);
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
 * nothing about which step is open. A Debrief step held until every Class game has finished says
 * so (Story 9.2); the current Debrief step leads to the Debrief of `sessionId`, the current Quiz
 * step to its step 5, the Debrief quiz (Story 9.9), and says when the Faglærer has changed the quiz
 * (Story 9.10). A current Debrief step says when a Group debrief the Student can join is under way
 * (Story 9.11); its link is the way in. A current Replay step says when the Testfrist has passed
 * with no Replay started (Story 10.3), or that a started one was closed there unfinished (Story
 * 10.6), and while the Replay runs «Fortsett Replay, Uke 9.» (Story
 * 10.4, UX-DR64), from the api's `replay` (AD-10); the way there is the Replay block's button just
 * above, so the step itself is no second Lenke. The current Individual test step leads to the test
 * (Story 11.3), and says when the Testfrist has passed without a hand-in (Story 11.11). A step a
 * Faglærer corrected says «gjort, rettet av faglærer» or «ikke gjort, …» whatever its state (Story
 * 13.3); its link stays. */
export function stepItems(
  steps: EnrolledSession["steps"],
  sessionId?: string,
  replay?: EnrolledSession["replay"],
): StegeneItem[] {
  const running = replay?.game?.status === "running" && replay.game.week != null ? replay.game : null;
  return (steps ?? []).map(({ step, state, held, quiz_changed, group_open, closed, counts, corrected }) => ({
    key: step,
    name: copy.stepNames[step],
    state,
    note: corrected
      ? // Story 13.3: a Faglærer corrected the step's status; the reason is never the Student's.
        copy.corrected(counts === true)
      : state === "current"
        ? quiz_changed && step === "quiz"
          ? copy.quizChanged
          : group_open && step === "debrief"
            ? copy.groupOpen
            : closed && step === "replay"
              ? // Story 10.6: a Replay started and closed at the Testfrist, or none started.
                replay?.game
                ? copy.replayClosedUnfinished
                : copy.replayClosed
              : closed && step === "test"
                ? // Story 11.11: the Testfrist passed without a hand-in.
                  copy.testClosed
                : running && step === "replay"
                  ? copy.replayResume(running.week!)
                  : copy.current
        : state === "done"
          ? // Story 13.1: a done step that does not count for the requirement says why.
            (counts === false ? copy.notCounted[step] : undefined) ?? copy.done
          : held && step === "debrief"
            ? copy.held.debrief
            : copy.locked[step],
    href: state === "current" && sessionId ? stepHref(step, sessionId) : undefined,
  }));
}

function stepHref(step: EnrolledSession["steps"][number]["step"], sessionId: string): string | undefined {
  if (step === "debrief") return DEBRIEF_PATH(sessionId);
  if (step === "quiz") return `${DEBRIEF_PATH(sessionId)}#debrief-quiz`;
  // Story 11.3: the current test step leads to the own-work statement, or the open test.
  if (step === "test") return TEST_PATH(sessionId);
  return undefined;
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

export function cardState(
  game: Pick<StudentGame, "status" | "briefing_first" | "seats" | "seat_state"> & { played_out?: boolean },
): CardState | null {
  // Story 8.14: a game the Play deadline playout took over waits for no one's Order.
  if (game.status !== "running" || game.briefing_first || !game.seat_state || game.played_out) return null;
  const own = game.seats.find((seat) => seat.mine);
  // A Seat an AI player took over has no Spillkort: Hjem says «KI-spiller har bestilt for deg.»
  if (!own || own.taken_over || own.ordered === null || own.ordered === undefined) return null;
  return own.ordered ? "ordered" : "waitsForYou";
}

/** «Netto lager −13 i Uke 11.»: what the Spillkort's hidden mini graph shows at nå, in words. */
export function netSentence(state: NonNullable<StudentGame["seat_state"]>): string {
  return copy.card.net(formatNumber(state.net_inventory), state.week);
}
