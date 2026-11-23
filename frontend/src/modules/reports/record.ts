import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import { formatNumber } from "@/lib/number-format";
import { osloDateText, osloDayAndTime } from "@/modules/sessions/dates";

const copy = nb.reports.completion;
const record = nb.reports.record;

/** The Studentside's record of one Student (Story 13.2, FR-63). */
export type StudentRecord = components["schemas"]["StudentRecordOut"];
export type Completion = components["schemas"]["CompletionOut"];
export type CompletionStep = components["schemas"]["CompletionStepOut"];
export type Participation = components["schemas"]["ParticipationOut"];

/** «70 %», the share as the spine writes it. */
export function percent(value: number): string {
  return `${formatNumber(value)} %`;
}

/** «ti. 12. des.»: the day of an instant, Europe/Oslo. */
export function day(iso: string): string {
  return osloDayAndTime(iso).day;
}

/** «12. des.»: the day of an instant without its weekday, Europe/Oslo. */
export function dayOfMonth(iso: string): string {
  return day(iso).replace(/^\S+\s/, "");
}

/** One row of «Fullføring»: the step's name, «gjort» or «ikke gjort» in text (UX-DR54), and the
 * lines under it: when the step event was recorded, why a recorded step does not count, and on
 * the Klassespill row the share lines (FR-17). A corrected step (Story 13.3) reads «Gjort, rettet
 * av Bård 12. des.» with the Faglærer's reason under it. */
export type CompletionRow = {
  step: string;
  name: string;
  done: boolean;
  status: string;
  corrected: boolean;
  reason: string | null;
  lines: string[];
};

export function completionRows(completion: Completion): CompletionRow[] {
  return completion.steps.map((step) => {
    const lines: string[] = [];
    if (step.recorded && step.recorded_at) lines.push(copy.recorded(day(step.recorded_at)));
    if (step.recorded && !step.done && !step.corrected && copy.notCounted[step.step]) {
      lines.push(copy.notCounted[step.step]!);
    }
    if (step.step === "class_game") lines.push(...shareLines(completion));
    const correction = step.corrected ? step.correction : null;
    return {
      step: step.step,
      name: copy.steps[step.step] ?? step.step,
      done: step.done,
      status: correction
        ? copy.corrected(correction.done, correction.by ?? copy.someone, dayOfMonth(correction.at))
        : step.done
          ? copy.done
          : copy.notDone,
      corrected: correction != null,
      reason: correction?.reason ?? null,
      lines,
    };
  });
}

/** «Bestilte i 70 % av ukene. Kravet er 80 %.» (the requirement only when obligatory) and, where
 * some Weeks were played out, «20 % av ukene ble spilt i utspillingen ved Spillfristen.» Nothing
 * before the game has its snapshot. With an Oppfølgingsspill (Story 13.4) the line names the game
 * the share comes from: «Bestilte i 100 % av ukene i Oppfølgingsspillet.» */
export function shareLines(completion: Completion): string[] {
  if (completion.ordered_share == null) return [];
  const ordered = completion.share_game
    ? copy.orderedIn(percent(completion.ordered_share), completion.share_game)
    : copy.ordered(percent(completion.ordered_share));
  const required = completion.adjusted
    ? copy.requiredAdjusted(percent(completion.required_share))
    : copy.required(percent(completion.required_share));
  const lines = [completion.obligatory ? `${ordered} ${required}` : ordered];
  if (completion.playout_share != null && completion.playout_share > 0) {
    lines.push(copy.playout(percent(completion.playout_share)));
  }
  return lines;
}

/** «Kravet er oppfylt.» / «Kravet er ikke oppfylt.», only for an obligatory Class session. */
export function requirementLine(completion: Completion): string | null {
  if (!completion.obligatory || completion.requirement_met == null) return null;
  return completion.requirement_met ? copy.met : copy.notMet;
}

/** «1 t 4 min» from whole seconds, rounded down to the minute; «under 1 min» below a minute. */
export function duration(seconds: number): string {
  if (seconds < 60) return copy.underMinute;
  const minutes = Math.floor(seconds / 60);
  return copy.hoursMinutes(Math.floor(minutes / 60), minutes % 60);
}

/** The participation lines (FR-17), information only: the time on the Student's own Orders and
 * whether those after the Guided Weeks were constant. */
export function participationLines(participation: Participation | null | undefined): string[] {
  if (!participation || participation.own_orders === 0) return [copy.noOrders];
  const count = participation.after_guided;
  const constant =
    participation.constant == null ? copy.tooFew : participation.constant ? copy.constant(count) : copy.varied(count);
  return [copy.timeSpent(duration(participation.seconds)), constant];
}

/** The game part's lines: «Spill 3 · Grossist» («Oppfølgingsspill · Grossist» once a finished
 * Oppfølgingsspill is the Student's game, Story 13.5), where it stands, and when it finished. */
export function gameLines(game: StudentRecord["game"], role: (role: string) => string): string[] {
  if (!game) return [record.game.none];
  const name = game.makeup ? record.game.makeup : record.game.name(game.number ?? null);
  const lines = [record.game.line(name, role(game.role))];
  lines.push(
    game.state === "finished" && game.finished_at
      ? record.game.finishedOn(day(game.finished_at))
      : (record.game.state[game.state] ?? ""),
  );
  if (game.played_out) lines.push(record.game.playedOut);
  return lines.filter(Boolean);
}

/** The Debrief part's summary line: not finished, or finished with its day and moments, and late. */
export function debriefLines(debrief: StudentRecord["debrief"]): string[] {
  if (!debrief.finished_at) return [record.debrief.notFinished];
  const lines = [record.debrief.finished(day(debrief.finished_at), debrief.moments)];
  if (debrief.late) lines.push(record.debrief.late);
  return lines;
}

/** One line per Debrief quiz attempt: «Forsøk 2 · ti. 12. des. kl. 10:00 · bestått». */
export function quizLines(quiz: StudentRecord["quiz"]): string[] {
  if (quiz.length === 0) return [record.quiz.none];
  return quiz.map((a) => record.quiz.attempt(a.number, osloDateText(a.submitted_at), a.passed));
}

/** The Replay part's line. */
export function replayLine(replay: StudentRecord["replay"]): string {
  if (!replay) return record.replay.none;
  return replay.finished_at ? record.replay.finishedOn(day(replay.finished_at)) : record.replay.running;
}

/** The Individual test part: its status, when it was handed in, and each part that holds content
 * or not (never the answers). */
export function testLines(test: StudentRecord["test"]): { lines: string[]; parts: { name: string; text: string }[] } {
  if (!test) return { lines: [record.test.none], parts: [] };
  const lines = [record.test.status[test.status] ?? ""];
  if (test.submitted_at) lines.push(record.test.submittedAt(osloDateText(test.submitted_at)));
  const parts = Object.entries(test.parts).map(([part, answered]) => ({
    name: record.test.parts[part] ?? part,
    text: answered ? record.test.answered : record.test.unanswered,
  }));
  return { lines: lines.filter(Boolean), parts };
}

/** The Oppfølgingsspill on the Klassespill row (Story 13.4): «Oppfølgingsspill gitt 12. des. Åpent
 * til fr. 18. des.», then where it stands. */
export function makeupLines(makeup: StudentRecord["makeup"]): { given: string; state: string } | null {
  if (!makeup) return null;
  const given = dayOfMonth(makeup.given_at);
  return {
    given: makeup.open_until
      ? copy.makeup.given(given, day(makeup.open_until))
      : copy.makeup.givenOn(given),
    state: copy.makeup.state[makeup.state] ?? "",
  };
}
