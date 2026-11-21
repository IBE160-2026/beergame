import { describe, expect, it } from "vitest";

import { GROUP, KRONER } from "@/lib/number-format";

import type { GameWeeks, OverviewGame } from "./api";
import { sortRows } from "@/components/charts/matrix-table-sort";

import {
  cellValues,
  clockWithSeconds,
  costText,
  filterGroups,
  groupsOf,
  headline,
  netValues,
  seatTexts,
  statusCounts,
  TABLE_COLUMNS,
  TABLE_SORT,
  tableRows,
  waitLines,
  wallGroups,
} from "./overview";

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

function weeksOf(gameId: string, nets: number[]): GameWeeks {
  return {
    game_id: gameId,
    version: 1,
    weeks: nets.map((net, i) => ({
      week: i + 1,
      seats: [
        { role: "retailer", net_inventory: 99, order: 4, cost: "1.0000" },
        { role: "factory", net_inventory: net, order: null, cost: "2.0000" },
      ],
    })),
  };
}

describe("wallGroups (Story 7.2)", () => {
  const now = Date.parse("2026-11-21T12:00:00Z");
  const groups = groupsOf([
    game({
      game_number: 2,
      status: "waiting",
      chain_cost: "1058.4000",
      wait_started_at: "2026-11-20T13:00:00Z",
      waiting_for: [{ role: "wholesaler", name: "Noah", since: "2026-11-20T13:00:00Z" }],
    }),
    game({ game_number: 4, status: "finished", chain_cost: "980.0000" }),
    game({ game_number: 7, status: "running" }),
  ]);

  it("keeps the Oversikt's groups and order, with the count in each header", () => {
    const wall = wallGroups(groups, new Map(), "factory", now);
    expect(wall.map((g) => [g.title, g.rows.map((r) => r.label)])).toEqual([
      ["Venter 1", ["Spill 2"]],
      ["Pågår 1", ["Spill 7"]],
      ["Ferdig, lavest kjedekost øverst 1", ["Spill 4"]],
    ]);
  });

  it("labels a row with game, status or wait and kjedekost, and reads them in its header", () => {
    const [waiting, running, finished] = wallGroups(groups, new Map(), "factory", now).map((g) => g.rows[0]!);
    expect(waiting!.figure).toBe(`1${GROUP}058`);
    expect(waiting!.detail).toBe("Venter på Noah (Grossist), 23 t");
    expect(waiting!.rowName).toBe(`Spill 2, venter på Noah (Grossist), 23 t, kjedekost 1${GROUP}058${KRONER}`);
    expect(running!.detail).toBe("Pågår");
    expect(running!.rowName).toBe("Spill 7, pågår");
    expect(finished!.rowName).toBe(`Spill 4, ferdig, kjedekost 980${KRONER}`);
  });

  it("takes the chosen Role's Netto lager as the api sent it, and marks a game still loading", () => {
    const weeks = new Map([["g2", { data: weeksOf("g2", [12, -3, -13]), failed: false }]]);
    const [waiting, running] = wallGroups(groups, weeks, "factory", now).map((g) => g.rows[0]!);
    expect(waiting!.values).toEqual([12, -3, -13]);
    expect(waiting!.loading).toBe(false);
    expect(running!.values).toEqual([]);
    expect(running!.loading).toBe(true);
    expect(netValues(weeksOf("g", [5]), "retailer")).toEqual([99]);
    expect(netValues(undefined, "factory")).toEqual([]);
  });
});

describe("tableRows (Story 7.3)", () => {
  const now = Date.parse("2026-11-21T12:00:00Z");
  const groups = groupsOf([
    game({
      game_number: 2,
      status: "waiting",
      chain_cost: "1058.4000",
      wait_started_at: "2026-11-20T13:00:00Z",
      waiting_for: [
        { role: "wholesaler", name: "Noah", since: "2026-11-20T13:00:00Z" },
        { role: "retailer", name: null, since: "2026-11-21T11:00:00Z" },
      ],
    }),
    game({
      game_number: 3,
      status: "waiting",
      chain_cost: "400.0000",
      wait_started_at: "2026-11-21T11:30:00Z",
      waiting_for: [{ role: "factory", name: "Ida", since: "2026-11-21T11:30:00Z" }],
    }),
    game({ game_number: 4, status: "finished", chain_cost: "980.0000" }),
    game({ game_number: 7, status: "running", chain_cost: "120.0000" }),
    game({ game_number: 9, status: "not_started" }),
  ]);
  const weeks = new Map([
    ["g2", { data: weeksOf("g2", [12, -3, -13]), failed: false }],
    ["g4", { data: weeksOf("g4", [0]), failed: false }],
    ["g7", { data: undefined, failed: true }],
  ]);
  const rows = tableRows(groups, weeks, "factory", now);
  const order = (sort: Parameters<typeof sortRows>[1]) => sortRows(rows, sort).map((row) => row.label);

  it("lists every game in the wall's order with status, whom it waits for and kjedekost as text", () => {
    expect(rows.map((row) => row.label)).toEqual(["Spill 2", "Spill 3", "Spill 7", "Spill 9", "Spill 4"]);
    expect(rows[0]!.cells).toEqual({
      status: "Venter",
      wait: "Noah (Grossist), 23 t; Detaljist, 1 t",
      cost: `1${GROUP}058`,
    });
    expect(rows[3]!.cells).toEqual({ status: "Ikke startet", wait: "", cost: "" });
    expect(TABLE_COLUMNS.map((column) => column.header)).toEqual(["Status", "Venter på", "Kjedekost, kr"]);
  });

  it("carries the same Netto lager as the wall; a failed fetch leaves cells empty, a pending one loads", () => {
    expect(rows[0]!.values).toEqual([12, -3, -13]);
    expect(rows[2]!).toMatchObject({ values: [], loading: false });
    expect(rows[1]!).toMatchObject({ values: [], loading: true });
    expect(rows[3]!).toMatchObject({ values: [], loading: false });
  });

  it("opens in the wall's order (status ascending) and reverses it descending", () => {
    expect(order(TABLE_SORT)).toEqual(["Spill 2", "Spill 3", "Spill 7", "Spill 9", "Spill 4"]);
    expect(order({ key: "status", direction: "descending" })).toEqual(["Spill 4", "Spill 9", "Spill 7", "Spill 3", "Spill 2"]);
    expect(order({ key: "game", direction: "ascending" })).toEqual(["Spill 2", "Spill 3", "Spill 4", "Spill 7", "Spill 9"]);
  });

  it("sorts the longest wait first, games that wait for nobody after it in the wall's order", () => {
    expect(order({ key: "wait", direction: "descending" })).toEqual(["Spill 2", "Spill 3", "Spill 7", "Spill 9", "Spill 4"]);
    expect(order({ key: "wait", direction: "ascending" })).toEqual(["Spill 3", "Spill 2", "Spill 7", "Spill 9", "Spill 4"]);
  });

  it("sorts by kjedekost both ways, a game not started last both times", () => {
    expect(order({ key: "cost", direction: "ascending" })).toEqual(["Spill 7", "Spill 3", "Spill 4", "Spill 2", "Spill 9"]);
    expect(order({ key: "cost", direction: "descending" })).toEqual(["Spill 2", "Spill 4", "Spill 3", "Spill 7", "Spill 9"]);
  });
});

describe("Veggfiltre on the rows received (Story 7.4, AD-10)", () => {
  const games = [
    game({ game_number: 1, status: "running" }),
    game({
      game_number: 2,
      status: "waiting",
      wait_started_at: "2026-11-21T10:00:00Z",
      seats: [{ role: "factory", holder: "student", name: "Ida" }],
    }),
    game({ game_number: 3, status: "finished", chain_cost: "900.0000" }),
    game({ game_number: 4, status: "finished", chain_cost: "800.0000", seats: [] }),
  ];
  const groups = groupsOf(games);
  const numbers = (status: Parameters<typeof filterGroups>[1]) =>
    filterGroups(groups, status).map((g) => [g.name, g.games.map((x) => x.game_number)]);

  it("keeps only the chosen status's group, or the games with an AI player in each group", () => {
    expect(numbers("all")).toEqual([
      ["waiting", [2]],
      ["running", [1]],
      ["finished", [4, 3]],
    ]);
    expect(numbers("finished")).toEqual([["finished", [4, 3]]]);
    expect(numbers("with_ai")).toEqual([
      ["running", [1]],
      ["finished", [3]],
    ]);
    expect(numbers("not_started")).toEqual([]);
  });

  it("counts every Status choice over the received games", () => {
    expect(statusCounts(games)).toEqual({ all: 4, waiting: 1, running: 1, not_started: 0, finished: 2, with_ai: 2 });
  });

  it("takes the chosen cells: Ordre up to the first Uke without one, Kost per uke as a number", () => {
    const weeks: GameWeeks = {
      game_id: "g",
      version: 1,
      weeks: [
        { week: 1, seats: [{ role: "factory", net_inventory: 12, order: 4, cost: "6.0000" }] },
        { week: 2, seats: [{ role: "factory", net_inventory: -3, order: 8, cost: "3.5000" }] },
        { week: 3, seats: [{ role: "factory", net_inventory: -9, order: null, cost: "9.0000" }] },
      ],
    };
    expect(cellValues(weeks, "factory", "net")).toEqual([12, -3, -9]);
    expect(cellValues(weeks, "factory", "order")).toEqual([4, 8]);
    expect(cellValues(weeks, "factory", "cost")).toEqual([6, 3.5, 9]);
    const rows = wallGroups(groupsOf([game({ game_number: 1, status: "running" })]), new Map([["g1", { data: weeks, failed: false }]]), "factory", 0, "order");
    expect(rows[0]!.rows[0]!.values).toEqual([4, 8]);
  });
});
