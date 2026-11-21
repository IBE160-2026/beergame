import { describe, expect, it } from "vitest";

import { GROUP, KRONER } from "@/lib/number-format";

import type { OverviewGame } from "./api";
import { clockWithSeconds, costText, groupsOf, headline, seatTexts, waitLines } from "./overview";

const HOUR = 3_600_000;

function game(over: Partial<OverviewGame> & Pick<OverviewGame, "game_number" | "status">): OverviewGame {
  return {
    game_id: `g${over.game_number}`,
    week: 4,
    version: 1,
    chain_cost: null,
    wait_started_at: null,
    waiting_for: [],
    seats: [
      { role: "factory", holder: "student", name: "Mikkel" },
      { role: "distributor", holder: "ai", name: null },
      { role: "wholesaler", holder: "student", name: null },
      { role: "retailer", holder: "free", name: null },
    ],
    ...over,
  };
}

describe("headline", () => {
  it("reads «41 ferdig · 15 pågår · 4 venter» and adds the games not started only when there are any", () => {
    expect(headline({ finished: 41, running: 15, waiting: 4, not_started: 0 })).toBe("41 ferdig · 15 pågår · 4 venter");
    expect(headline({ finished: 0, running: 1, waiting: 0, not_started: 3 })).toBe(
      "0 ferdig · 1 pågår · 0 venter · 3 ikke startet",
    );
  });
});

describe("groupsOf", () => {
  it("groups Venter, Pågår, Ikke startet, Ferdig; longest wait first, lowest chain cost first, empty groups out", () => {
    const groups = groupsOf([
      game({ game_number: 5, status: "finished", chain_cost: "1200.0000" }),
      game({ game_number: 1, status: "running" }),
      game({ game_number: 2, status: "waiting", wait_started_at: "2026-11-21T10:00:00Z" }),
      game({ game_number: 3, status: "waiting", wait_started_at: "2026-11-21T08:00:00Z" }),
      game({ game_number: 4, status: "finished", chain_cost: "980.5000" }),
    ]);
    expect(groups.map((g) => [g.title, g.games.map((x) => x.game_number)])).toEqual([
      ["Venter", [3, 2]],
      ["Pågår", [1]],
      ["Ferdig, lavest kjedekost øverst", [4, 5]],
    ]);
    expect(groupsOf([game({ game_number: 9, status: "not_started" })])[0]!.title).toBe("Ikke startet");
  });
});

describe("waitLines", () => {
  it("names the waited-for Student with Role and duration, by Role alone when no name can be shown", () => {
    const now = Date.parse("2026-11-21T12:00:00Z");
    const waiting = game({
      game_number: 2,
      status: "waiting",
      waiting_for: [
        { role: "wholesaler", name: "Noah", since: new Date(now - 23 * HOUR).toISOString() },
        { role: "retailer", name: null, since: new Date(now - 5 * 60_000).toISOString() },
      ],
    });
    expect(waitLines(waiting, now)).toEqual(["Venter på Noah (Grossist), 23 t", "Venter på Detaljist, 5 min"]);
  });
});

describe("seatTexts and costText", () => {
  it("words each Seat in the api's order and the cost in whole kroner", () => {
    expect(seatTexts(game({ game_number: 1, status: "running" }))).toEqual([
      "Fabrikk: Mikkel",
      "Distributør: KI-spiller",
      "Grossist: Student",
      "Detaljist: Ledig",
    ]);
    expect(costText(game({ game_number: 1, status: "running", chain_cost: "1058.4900" }))).toBe(`1${GROUP}058${KRONER}`);
    expect(costText(game({ game_number: 1, status: "not_started" }))).toBeNull();
  });
});

describe("clockWithSeconds", () => {
  it("reads Europe/Oslo time with seconds", () => {
    expect(clockWithSeconds(Date.parse("2026-11-21T13:02:15Z"))).toBe("14:02:15");
  });
});
