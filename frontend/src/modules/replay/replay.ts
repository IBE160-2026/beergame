import { nb } from "@/copy/nb";
import { roleName } from "@/modules/sessions/sessions";

import type { StudentReplay } from "./api";

const copy = nb.homes.student.replay;

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
