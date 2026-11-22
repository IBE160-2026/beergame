import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { stepItems } from "@/modules/games/home";

import type { StudentReplay } from "./api";
import { replayTitle, resumeWeek, wantsReplayPrimary } from "./replay";

const STARTED: StudentReplay = {
  can_start: false,
  game: {
    id: "01a1f8ee-34f2-70af-8800-f79281ed777e",
    role: "wholesaler",
    status: "running",
    week: 1,
    server_now: "2026-11-22T10:00:00Z",
    seats: [],
  },
};

describe("the Replay on Hjem (Story 10.3)", () => {
  it("names the Role once started and only «Replay» before", () => {
    expect(replayTitle(STARTED)).toBe("Replay · Du er Grossist");
    expect(replayTitle({ can_start: true, game: null })).toBe("Replay");
  });

  it("asks for the primary button to start it, and to go on with it while it runs (Story 10.4)", () => {
    expect(wantsReplayPrimary({ can_start: true, game: null })).toBe(true);
    expect(wantsReplayPrimary({ can_start: false, game: null })).toBe(false);
    expect(wantsReplayPrimary(STARTED)).toBe(true);
    expect(wantsReplayPrimary({ ...STARTED, game: { ...STARTED.game!, status: "finished", week: null } })).toBe(false);
    expect(wantsReplayPrimary(null)).toBe(false);
    expect(resumeWeek({ ...STARTED, game: { ...STARTED.game!, week: 9 } })).toBe(9);
    expect(resumeWeek({ ...STARTED, game: { ...STARTED.game!, status: "ready", week: null } })).toBeNull();
  });

  it("says in Stegene's Replay step to go on at the open Uke while it runs (Story 10.4)", () => {
    const steps = [
      { step: "replay" as const, state: "current" as const, held: false, quiz_changed: false, group_open: false, closed: false },
    ];
    const [running] = stepItems(steps, "s1", { ...STARTED, game: { ...STARTED.game!, week: 9 } });
    expect(running.note).toBe("Fortsett Replay, Uke 9.");
    expect(running.href).toBeUndefined(); // the Replay block's button above is the way there
    const [none] = stepItems(steps, "s1", { can_start: true, game: null });
    expect(none.href).toBeUndefined();
    expect(none.note).toBe(nb.homes.student.current);
  });

  it("says in Stegene when the Testfrist has passed with no Replay", () => {
    const [replay] = stepItems([
      {
        step: "replay",
        state: "current",
        held: false,
        quiz_changed: false,
        group_open: false,
        closed: true,
      },
    ]);
    expect(replay.note).toBe(nb.homes.student.replayClosed);
    const [open] = stepItems([
      {
        step: "replay",
        state: "current",
        held: false,
        quiz_changed: false,
        group_open: false,
        closed: false,
      },
    ]);
    expect(open.note).toBe(nb.homes.student.current);
  });
});
