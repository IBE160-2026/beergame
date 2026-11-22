import { nb } from "@/copy/nb";
import { roleName } from "@/modules/sessions/sessions";

import type { StudentReplay } from "./api";

const copy = nb.homes.student.replay;

/** «Replay · Du er Grossist» once started; «Replay» before. */
export function replayTitle(replay: StudentReplay): string {
  return replay.game ? copy.title(roleName(replay.game.role)) : copy.heading;
}

/** Whether the Replay asks for Hjem's one primary button (UX-DR8): only «Start Replay», while
 * the api says it may start. From the api's `can_start` alone (AD-10). */
export function wantsReplayPrimary(
  replay: StudentReplay | null | undefined,
): boolean {
  return replay?.can_start === true;
}
