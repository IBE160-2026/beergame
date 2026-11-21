import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { OverviewGame } from "./api";
import { filterGroups, groupsOf, headline, statusCounts, statusLines, wallGroups } from "./overview";
import { PauseControl, PauseLine, pauseText } from "./pause-view";
import { Spillstyring } from "./spillstyring";

/** Story 8.6 (FR-89, FR-39, UX-DR26, UX-DR45, UX-DR62): the Pausevalg and the pause lines on Spill
 * and Hjem, and the paused game on the Oversikt. The api decides; the page words it. */
const copy = nb.homes.student.pause;

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

describe("the pause line", () => {
  it("names who paused, or who ordered and so ended it, and never a Week count", () => {
    expect(pauseText({ state: "paused", name: "Sara", mine: false })).toBe("Pause, satt av Sara.");
    expect(pauseText({ state: "paused", name: "Sara", mine: true })).toBe(copy.pausedByYou);
    expect(pauseText({ state: "paused", name: null, mine: false })).toBe(copy.pausedByUnknown);
    expect(pauseText({ state: "ended", name: "Jonas", mine: false })).toBe("Pausen er over. Jonas har bestilt.");
    expect(pauseText({ state: "ended", name: "Jonas", mine: true })).toBe(copy.endedByYou);
    expect(pauseText({ state: "ended", name: null, mine: false })).toBe(copy.endedByUnknown);
    expect(pauseText(null)).toBe("");
    for (const line of [copy.pausedByYou, copy.pausedByUnknown, copy.endedByYou, copy.endedByUnknown]) {
      expect(line).not.toMatch(/\d|uke/i);
    }
  });

  it("is a polite live region that is always there, filled once drawn so it is also read on load", () => {
    const line = html(<PauseLine gameId="g1" pause={{ state: "paused", name: "Sara", mine: false }} />);
    expect(line).toBe('<div aria-live="polite" data-pause-line="paused"></div>');
  });
});

describe("«Ta pause»", () => {
  it("is a secondary button, full width below 1024 px, only while the api says the reader may pause", () => {
    const control = html(<PauseControl gameId="g1" canPause />);
    expect(control).toMatch(/<button[^>]*data-pause-open=""[^>]*>Ta pause<\/button>/);
    const button = control.match(/<button[^>]*>/)?.[0] ?? "";
    expect(button).toContain("w-full lg:w-auto");
    expect(button).not.toContain("bg-ink"); // never the primary
    expect(html(<PauseControl gameId="g1" canPause={false} />)).toBe("");
  });

  it("carries the epic's Pausevalg copy, with no date or time", () => {
    expect(copy.noTakeover).toBe("Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.");
    expect(copy.onlyLecturer).toBe(
      "Bare faglæreren kan avtale et tidspunkt. Uten det har hver av dere sin vanlige ventetid før en KI-spiller kan settes inn.",
    );
    expect(copy.cancel).toBe("Avbryt");
    expect(copy.confirm).toBe("Ta pause uten avtalt tid");
  });
});

const game = (over: Partial<OverviewGame>): OverviewGame => ({
  game_id: "g",
  game_number: 1,
  status: "running",
  week: 3,
  version: 1,
  chain_cost: null,
  wait_started_at: null,
  waiting_for: [],
  seats: [],
  ...over,
});

describe("the Oversikt with a paused game", () => {
  const paused = game({
    game_id: "p",
    game_number: 4,
    status: "paused",
    paused_at: "2026-11-23T13:10:00Z",
    paused_by: "Sara",
  });
  const games = [
    game({ game_id: "r", game_number: 1 }),
    paused,
    game({ game_id: "w", game_number: 2, status: "waiting", waiting_for: [{ role: "factory", name: "Jonas", since: "2026-11-23T12:00:00Z" }] }),
    game({ game_id: "p2", game_number: 3, status: "paused", paused_at: "2026-11-23T12:00:00Z", paused_by: null }),
  ];

  it("puts the group «Pause» between Venter and Pågår, the longest paused first", () => {
    const groups = groupsOf(games);
    expect(groups.map((g) => [g.title, g.games.map((x) => x.game_id)])).toEqual([
      ["Venter", ["w"]],
      ["Pause", ["p2", "p"]],
      ["Pågår", ["r"]],
    ]);
    expect(wallGroups(groups, new Map(), "factory", Date.parse("2026-11-23T14:00:00Z")).map((g) => g.title)).toEqual([
      "Venter 1",
      "Pause 2",
      "Pågår 1",
    ]);
  });

  it("says since when and by whom, in Europe/Oslo, in the list and the wall row", () => {
    expect(statusLines(paused, 0)).toEqual(["Pause siden ma. 14:10, satt av Sara."]);
    expect(statusLines(games[3]!, 0)).toEqual(["Pause siden ma. 13:00."]);
    const [row] = wallGroups(groupsOf([paused]), new Map(), "factory", Date.parse("2026-11-23T14:00:00Z"))[0]!.rows;
    expect(row!.detail).toBe("Pause siden ma. 14:10, satt av Sara.");
    expect(row!.shortDetail).toBe("Pause");
    expect(row!.rowName).toContain("pause siden ma. 14:10, satt av Sara.");
  });

  it("keeps Spillstyring's per-Seat action on a paused game", () => {
    const seat = { role: "factory" as const, holder: "student" as const, name: "Jonas", user_id: "u", links: [], mark: null, mark_by: null };
    const data = {
      game_id: "g1",
      class_session_id: "s1",
      class_id: "c1",
      class_name: "Klasse",
      session_number: 1,
      game_number: 2,
      status: "paused" as const,
      version: 1,
      weeks_total: 20,
      demand: [],
      seats: [{ ...seat, takeover: "this_week" as const }],
      roles: [],
    };
    expect(html(<Spillstyring data={data} />)).toContain('data-takeover="factory"');
  });

  it("counts it as running, «herav n pauset», and the «Pågår» filter takes it", () => {
    expect(headline({ finished: 41, running: 15, waiting: 4, not_started: 0, paused: 2 })).toBe(
      "41 ferdig · 15 pågår (herav 2 pauset) · 4 venter",
    );
    expect(statusCounts(games).running).toBe(3);
    const running = filterGroups(groupsOf(games), "running");
    expect(running.map((g) => g.name)).toEqual(["paused", "running"]);
    expect(filterGroups(groupsOf(games), "waiting").map((g) => g.name)).toEqual(["waiting"]);
  });
});
