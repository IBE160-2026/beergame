import { describe, expect, it } from "vitest";

import { GROUP, KRONER } from "@/lib/number-format";

import type { ClassOverview, GameWeeks, OverviewGame } from "./api";
import { sortRows } from "@/components/charts/matrix-table-sort";

import {
  aiLine,
  cellValues,
  costRows,
  costSummary,
  funnelRows,
  roleBars,
  waitingElsewhere,
  changedGames,
  type ClassCost,
  clockWithSeconds,
  costText,
  filterGroups,
  groupsOf,
  headline,
  holdGroups,
  netValues,
  orderOf,
  readAgainAt,
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
    expect(waiting!.shortDetail).toBe("Venter, 23 t");
    expect(running!.detail).toBe("Pågår");
    expect(running!.shortDetail).toBe("Pågår");
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

describe("changedGames (Story 7.5)", () => {
  const answer = (items: OverviewGame[]) =>
    ({ items, counts: { waiting: 0, running: 0, not_started: 0, finished: 0 } }) as unknown as ClassOverview;
  const one = game({ game_number: 1, status: "running" });
  const two = game({ game_number: 2, status: "running" });

  it("counts the games with another version, added or dropped", () => {
    const held = answer([one, two]);
    expect(changedGames(held, answer([{ ...one, version: 2 }, two]), false)).toBe(1);
    expect(changedGames(held, answer([{ ...one, version: 3 }, { ...two, version: 2 }]), false)).toBe(2);
    expect(changedGames(held, answer([one]), false)).toBe(1);
    expect(changedGames(answer([one]), answer([one, two]), false)).toBe(1);
  });

  it("is 0 for the same answer and at least 1 for any other", () => {
    const held = answer([one]);
    expect(changedGames(held, held, true)).toBe(0);
    expect(changedGames(held, answer([one]), false)).toBe(1);
  });
});

describe("holdGroups (Story 7.5)", () => {
  const one = game({ game_number: 1, status: "running" });
  const two = game({ game_number: 2, status: "running" });
  const three = game({ game_number: 3, status: "waiting", wait_started_at: "2026-11-21T10:00:00Z" });

  it("keeps a game that changed status where it stood, with its new values", () => {
    const held = orderOf(groupsOf([one, two]));
    const moved = { ...one, status: "waiting" as const, version: 2, wait_started_at: "2026-11-21T10:00:00Z" };
    const now = groupsOf([moved, two]);
    expect(now.map((g) => g.name)).toEqual(["waiting", "running"]);
    const kept = holdGroups(now, held);
    expect(kept.map((g) => [g.name, g.games.map((x) => x.game_number)])).toEqual([["running", [1, 2]]]);
    expect(kept[0]!.games[0]!.version).toBe(2);
  });

  it("drops a game that left and adds a new one at the end of its group, or in a group after", () => {
    const held = orderOf(groupsOf([one, two]));
    const kept = holdGroups(groupsOf([two, three, game({ game_number: 4, status: "running" })]), held);
    expect(kept.map((g) => [g.name, g.games.map((x) => x.game_number)])).toEqual([
      ["running", [2, 4]],
      ["waiting", [3]],
    ]);
  });

  it("keeps a held game outside the Status filter and lets in only new games the filter admits", () => {
    const held = orderOf(groupsOf([one, two]));
    const moved = { ...one, status: "waiting" as const, version: 2, wait_started_at: "2026-11-21T10:00:00Z" };
    const kept = holdGroups(groupsOf([moved, two, three]), held, (g) => g.status === "running");
    expect(kept.map((g) => [g.name, g.games.map((x) => x.game_number)])).toEqual([["running", [1, 2]]]);
  });
});

describe("readAgainAt (Story 7.5, AD-8)", () => {
  it("reads again 1 s after the api's clock reaches the Start date, whatever the browser's clock says", () => {
    // The api says 30 s are left; the answer arrived at browser time 5 000 (its clock is off by hours).
    expect(readAgainAt("2026-11-21T13:00:30Z", "2026-11-21T13:00:00Z", 5_000)).toBe(36_000);
  });
});

describe("the right rail (Story 7.6, AD-10)", () => {
  const now = Date.parse("2026-11-21T12:00:00Z");

  it("lists the waiting games longest wait first, each with whom and how long", () => {
    const groups = groupsOf([
      game({
        game_number: 10,
        status: "waiting",
        wait_started_at: "2026-11-21T00:00:00Z",
        waiting_for: [{ role: "wholesaler", name: "Oskar", since: "2026-11-21T00:00:00Z" }],
      }),
      game({
        game_number: 30,
        status: "waiting",
        wait_started_at: "2026-11-20T18:00:00Z",
        waiting_for: [
          { role: "retailer", name: "Ida", since: "2026-11-20T18:00:00Z" },
          { role: "factory", name: null, since: "2026-11-21T10:00:00Z" },
        ],
      }),
      game({ game_number: 3, status: "running" }),
    ]);
    expect(waitingElsewhere(groups, now)).toEqual([
      { id: "g30", game: "Spill 30", who: ["Ida, Detaljist, 18 t", "Fabrikk, 2 t"] },
      { id: "g10", game: "Spill 10", who: ["Oskar, Grossist, 12 t"] },
    ]);
    expect(waitingElsewhere(groupsOf([game({ game_number: 1, status: "running" })]), now)).toEqual([]);
    expect(waitingElsewhere(groupsOf([game({ game_number: 4, status: "waiting" })]), now)).toEqual([
      { id: "g4", game: "Spill 4", who: ["Venter"] },
    ]);
  });

  it("words the AI line from the api's counts", () => {
    expect(aiLine({ seats: 22, games: 17 })).toBe("22 KI-spillere i 17 spill, alle merket.");
    expect(aiLine({ seats: 1, games: 1 })).toBe("1 KI-spiller i 1 spill, merket.");
    expect(aiLine({ seats: 0, games: 0 })).toBe("Ingen KI-spillere.");
  });

  const cost: ClassCost = {
    games: 3,
    median: "1954.4",
    lower_quartile: "1500",
    upper_quartile: "2600.5",
    holding_cost: "949.00",
    backorder_cost: "1063.00",
    roles: [
      { role: "retailer", holding_cost: "120.00", backorder_cost: "93.00", total_cost: "213.00" },
      { role: "wholesaler", holding_cost: "200.00", backorder_cost: "262.00", total_cost: "462.00" },
      { role: "distributor", holding_cost: "300.00", backorder_cost: "386.00", total_cost: "686.00" },
      { role: "factory", holding_cost: "329.00", backorder_cost: "322.00", total_cost: "651.00" },
    ],
  };

  it("prints the api's median and middle half in whole kroner", () => {
    expect(costSummary(cost)).toBe(`Median 1${GROUP}954. Midterste halvdel 1${GROUP}500–2${GROUP}601.`);
  });

  it("scales the Role bars to the costliest Role and prints each total", () => {
    const bars = roleBars(cost);
    expect(bars.map((bar) => [bar.name, bar.amount])).toEqual([
      ["Detaljist", "213"],
      ["Grossist", "462"],
      ["Distributør", "686"],
      ["Fabrikk", "651"],
    ]);
    expect(bars[2]!.holding + bars[2]!.backorder).toBeCloseTo(1);
    expect(bars[0]!.holding).toBeCloseTo(120 / 686);
    expect(bars[0]!.reads).toBe("Detaljist: lager 120, restordre 93, i alt 213 kr");
  });

  it("tables the finished games lowest chain cost first", () => {
    const rows = costRows([
      game({ game_number: 2, status: "finished", chain_cost: "2600.0000" }),
      game({ game_number: 5, status: "finished", chain_cost: "660.0000" }),
      game({ game_number: 7, status: "running", chain_cost: "10.0000" }),
    ]);
    expect(rows.map((row) => [row.game, row.cost])).toEqual([
      ["Spill 5", "660"],
      ["Spill 2", `2${GROUP}600`],
    ]);
  });

  it("names the Trakt's stages in the api's order and scales the bars to the largest count", () => {
    const rows = funnelRows([
      { stage: "registered", count: 240 },
      { stage: "class_game", count: 120 },
      { stage: "assessment_ready", count: 0 },
    ]);
    expect(rows.map((row) => [row.label, row.count, row.share])).toEqual([
      ["Registrert", 240, 1],
      ["Klassespill ferdig", 120, 0.5],
      ["KI-vurdering klar", 0, 0],
    ]);
    expect(funnelRows([{ stage: "registered", count: 0 }])[0]!.share).toBe(0);
  });
});
