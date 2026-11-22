import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { stepItems } from "@/modules/games/home";

import type { StudentReplay } from "./api";
import { replayTitle, wantsReplayPrimary } from "./replay";

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

  it("asks for the primary button only while the api says it may start", () => {
    expect(wantsReplayPrimary({ can_start: true, game: null })).toBe(true);
    expect(wantsReplayPrimary({ can_start: false, game: null })).toBe(false);
    expect(wantsReplayPrimary(STARTED)).toBe(false);
    expect(wantsReplayPrimary(null)).toBe(false);
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
