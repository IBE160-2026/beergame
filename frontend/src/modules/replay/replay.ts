import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import type { GameResult } from "@/modules/games/api";
import { roleName } from "@/modules/sessions/sessions";

import type { StudentReplay } from "./api";

const copy = nb.homes.student.replay;

/** «Replay er ferdig» in figures (Story 10.5, FR-50): the Student's own Totalkostnad, the api's
 * `total_cost` of their Role formatted by the shared formatter («1 592,00 kr»), and the line under
 * it. Null when the result has no row for the Role. */
export function replayEnd(
  result: GameResult,
  role: GameResult["roles"][number]["role"],
): { total: string; note: string } | null {
  const own = result.roles.find((row) => row.role === role);
  if (!own) return null;
  return {
    total: formatNumber(own.total_cost, { kroner: true }),
    note: nb.games.play.replayEnd.totalNote(roleName(role)),
  };
}

/** Whether a Replay on Hjem has finished, so its screen is offered to read again (Story 10.5). */
export function finishedReplay(replay: StudentReplay | null | undefined): boolean {
  return replay?.game?.status === "finished";
}

/** «Replay · Du er Grossist» once started; «Replay» before. */
export function replayTitle(replay: StudentReplay): string {
  return replay.game ? copy.title(roleName(replay.game.role)) : copy.heading;
}

/** The open Uke of a running Replay, for «Fortsett Replay, Uke 9» (Story 10.4); null when it does
 * not run. From the api's `status` and `week` alone (AD-10). */
export function resumeWeek(replay: StudentReplay | null | undefined): number | null {
  const game = replay?.game;
  return game?.status === "running" && game.week != null ? game.week : null;
}

/** Whether the Replay asks for Hjem's one primary button (UX-DR8): «Start Replay» while the api
 * says it may start, and «Fortsett Replay, Uke 9» while it runs (Story 10.4). From the api's
 * fields alone (AD-10). */
export function wantsReplayPrimary(
  replay: StudentReplay | null | undefined,
): boolean {
  return replay?.can_start === true || resumeWeek(replay) !== null;
}
