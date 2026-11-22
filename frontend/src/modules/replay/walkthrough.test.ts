import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { KRONER } from "@/lib/number-format";

import { pendingRefetch, type Walkthrough } from "./api";
import { unlikeReasons, walkthroughRows, walkthroughTotals, walkthroughView } from "./walkthrough";

const copy = nb.replay.walkthrough;

const week = (n: number, net: number, order: number, cost: string) => ({ week: n, net_inventory: net, order, total_cost: cost });

const ready: Walkthrough = {
  game_id: "g1",
  role: "wholesaler",
  state: "ready",
  retry_after_seconds: null,
  replay: { weeks: [week(1, 12, 4, "6.00"), week(2, -3, 12, "9.00")], total_cost: "9.00" },
  class_game: {
    weeks: [week(1, 12, 4, "6.00"), week(2, 8, 4, "10.00"), week(3, -1, 8, "11.0000")],
    total_cost: "11.0000",
    game_number: 17,
  },
  mostly_ai: false,
  moments: [],
  narration: null,
};

describe("Replay-gjennomgang (Story 10.7)", () => {
  it("chooses the view from the api's answer or error code alone", () => {
    expect(walkthroughView(undefined, "forbidden")).toBe("denied");
    expect(walkthroughView(undefined, "replay_closed")).toBe("closed");
    expect(walkthroughView(undefined, "replay_not_finished")).toBe("notFinished");
    expect(walkthroughView(undefined, null)).toBe("waiting");
    expect(walkthroughView({ ...ready, state: "pending", retry_after_seconds: 30 }, null)).toBe("pending");
    expect(walkthroughView(ready, null)).toBe("ready");
  });

  it("asks again after the api's wait while pending, never once ready", () => {
    expect(pendingRefetch({ ...ready, state: "pending", retry_after_seconds: 30 })).toBe(10_000);
    expect(pendingRefetch({ ...ready, state: "pending", retry_after_seconds: 4 })).toBe(4000);
    expect(pendingRefetch({ ...ready, state: "pending", retry_after_seconds: 0 })).toBe(1000);
    expect(pendingRefetch(ready)).toBe(false);
    expect(pendingRefetch(undefined)).toBe(false);
  });

  it("puts every Uke of either run in one table, the shorter run's missing Uker empty", () => {
    expect(walkthroughRows(ready)).toEqual([
      { week: 1, replay: { net: 12, order: "4", cost: `6,00${KRONER}` }, klass: { net: 12, order: "4", cost: `6,00${KRONER}` } },
      { week: 2, replay: { net: -3, order: "12", cost: `9,00${KRONER}` }, klass: { net: 8, order: "4", cost: `10,00${KRONER}` } },
      { week: 3, replay: null, klass: { net: -1, order: "8", cost: `11,00${KRONER}` } },
    ]);
    expect(walkthroughRows({ ...ready, class_game: null, mostly_ai: true }).map((row) => row.klass)).toEqual([null, null]);
  });

  it("says «Ikke like for like.» with the reasons in words, and formats both totals", () => {
    expect(unlikeReasons(ready)).toEqual([copy.unlikeNeighbours, copy.unlikeDemand, copy.unlikeWeeks(2, 3)]);
    expect(copy.unlikeWeeks(2, 3)).toBe("Replay hadde 2 uker, Klassespillet 3.");
    expect(copy.unlikeWeeks(3, 3)).toBe("Begge hadde 3 uker.");
    expect(walkthroughTotals(ready)).toEqual({ replay: `9,00${KRONER}`, klass: `11,00${KRONER}` });
    expect(walkthroughTotals({ ...ready, class_game: null })).toEqual({ replay: `9,00${KRONER}`, klass: null });
  });

  it("never ranks, praises or says which run was better", () => {
    const words = /bedre|best|verre|vant|tapte|flink|bra jobb|gratulerer|rangering|plass/i;
    for (const text of Object.values(copy)) {
      const shown = typeof text === "function" ? (text as (a: number, b: number) => string)(30, 36) : text;
      expect(shown).not.toMatch(words);
    }
  });
});
