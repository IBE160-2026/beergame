import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import type { GameResult } from "@/modules/games/api";
import result from "@/modules/games/fixtures/result-classic.json";
import { endTitle } from "@/modules/games/game-end";
import { stepItems } from "@/modules/games/home";

import type { StudentReplay } from "./api";
import { ReplayClosed } from "./replay-closed";
import { closedReplay, finishedReplay, replayEnd, replayTitle, resumeWeek, wantsReplayPrimary } from "./replay";

const classic = result as GameResult;
/** The formatter's narrow spaces as plain ones, so the expectations read as the screen does. */
const plain = (value: unknown): unknown => JSON.parse(JSON.stringify(value).replace(/[  ]/g, " "));

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
      { step: "replay" as const, state: "current" as const, held: false, quiz_changed: false, group_open: false, closed: false, corrected: false, after_makeup: false },
    ];
    const [running] = stepItems(steps, "s1", { ...STARTED, game: { ...STARTED.game!, week: 9 } });
    expect(running.note).toBe("Fortsett Replay, Uke 9.");
    expect(running.href).toBeUndefined(); // the Replay block's button above is the way there
    const [none] = stepItems(steps, "s1", { can_start: true, game: null });
    expect(none.href).toBeUndefined();
    expect(none.note).toBe(nb.homes.student.current);
  });

  it("offers a finished Replay to read again, never as the primary (Story 10.5)", () => {
    const finished = { ...STARTED, game: { ...STARTED.game!, status: "finished" as const, week: null } };
    expect(finishedReplay(finished)).toBe(true);
    expect(finishedReplay(STARTED)).toBe(false);
    expect(finishedReplay(null)).toBe(false);
    expect(wantsReplayPrimary(finished)).toBe(false);
  });

  it("gives «Replay er ferdig» the Student's own Totalkostnad, formatted (Story 10.5)", () => {
    const model = replayEnd(classic, "wholesaler");
    expect(plain(model)).toEqual({ total: "553,50 kr", note: "Grossist, to kostnadsarter, hele Replay." });
    expect(replayEnd({ ...classic, roles: [] }, "wholesaler")).toBeNull();
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
        corrected: false,
        after_makeup: false,
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
        corrected: false,
        after_makeup: false,
      },
    ]);
    expect(open.note).toBe(nb.homes.student.current);
  });

  it("tells a Replay closed at the Testfrist from a finished one (Story 10.6)", () => {
    const closed = {
      ...STARTED,
      game: { ...STARTED.game!, status: "finished" as const, week: null, end_reason: "test_deadline" as const },
    };
    expect(closedReplay(closed.game)).toBe(true);
    expect(finishedReplay(closed)).toBe(false); // no «Se Replay»
    expect(wantsReplayPrimary(closed)).toBe(false);
    const finished = { ...STARTED.game!, status: "finished" as const, week: null, end_reason: null };
    expect(closedReplay(finished)).toBe(false);
    expect(closedReplay(STARTED.game)).toBe(false);
    expect(closedReplay(null)).toBe(false);
    // Stegene: a started Replay closed there reads so; none started, as before.
    const steps = [
      { step: "replay" as const, state: "current" as const, held: false, quiz_changed: false, group_open: false, closed: true, corrected: false, after_makeup: false },
    ];
    expect(stepItems(steps, "s1", closed)[0]!.note).toBe(nb.homes.student.replayClosedUnfinished);
    expect(stepItems(steps, "s1", { can_start: false, game: null })[0]!.note).toBe(nb.homes.student.replayClosed);
    // The page title: «Replay stengt», never «Replay er ferdig».
    expect(endTitle({ replay: true, end_reason: "test_deadline" })).toBe("Replay stengt");
    expect(endTitle({ replay: true, end_reason: null })).toBe("Replay er ferdig");
    // Story 13.4: an Oppfølgingsspill closed at the Testfrist says so in its own words.
    expect(endTitle({ replay: false, makeup: true, end_reason: "test_deadline" })).toBe("Oppfølgingsspill stengt");
    expect(endTitle({ replay: false, makeup: true, end_reason: null })).toBe("Spillet er ferdig");
  });
});

describe("the closed screen of an Oppfølgingsspill (Story 13.4)", () => {
  it("names the Oppfølgingsspill, not the Replay", () => {
    expect(renderToStaticMarkup(<ReplayClosed makeup />)).toContain(nb.games.play.makeupClosed.lead);
    expect(renderToStaticMarkup(<ReplayClosed />)).toContain(nb.games.play.replayClosed.lead);
  });
});
