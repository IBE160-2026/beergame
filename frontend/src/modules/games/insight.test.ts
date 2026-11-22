import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameInsight, InsightWeek, SeatMark } from "./api";
import {
  chartWeeks,
  clockText,
  CUSTOMERS,
  hasWeeks,
  holderText,
  linkTexts,
  markText,
  orderRoles,
  orderTableRows,
  roleTables,
  seatMarkText,
  seatsUpstreamFirst,
  stockRoles,
  stockTableRows,
  weekRow,
} from "./insight";
import { InsightBody } from "./insight-page";

const copy = nb.insight;
const CHAIN = ["retailer", "wholesaler", "distributor", "factory"] as const;

const week = (n: number, extra: Partial<InsightWeek> = {}): InsightWeek => ({
  week: n,
  holder: "student",
  name: "Ida Berg",
  incoming_order: 4,
  incoming_delivery: 4,
  inventory: 12,
  backlog: 0,
  order: 5,
  cost: "6.0000",
  marks: [],
  opened_at: null,
  ordered_at: null,
  ...extra,
});

const insight = (weeks: InsightWeek[][]): GameInsight => ({
  game_id: "g",
  class_session_id: "s",
  class_id: "c",
  class_name: "class-of-2026",
  session_number: 1,
  game_number: 2,
  status: "running",
  version: 7,
  weeks_total: 36,
  can_pause: false,
  can_adjust: false,
  demand: [],
  seats: [
    { role: "retailer", holder: "student", name: "Ida Berg", links: [], extra_time: false },
    { role: "wholesaler", holder: "ai", name: null, links: [], extra_time: false },
    { role: "distributor", holder: "free", name: null, links: [], extra_time: false },
    {
      role: "factory",
      holder: "student",
      name: null,
      links: [
        { kind: "explanation", href: "/f" },
        { kind: "later_kind", href: "/g" },
      ],
      extra_time: false,
    },
  ],
  roles: CHAIN.map((role, i) => ({ role, weeks: weeks[i] ?? [], first_large_order_week: null })),
});

describe("Spillinnsikt's words (Story 7.7)", () => {
  it("puts the Seats upstream first and names each holder", () => {
    const seats = seatsUpstreamFirst(insight([]));
    expect(seats.map((s) => s.role)).toEqual(["factory", "distributor", "wholesaler", "retailer"]);
    expect(seats.map(holderText)).toEqual([copy.unknownStudent, copy.freeSeat, copy.aiPlayer, "Ida Berg"]);
  });

  it("says why an AI player holds a Seat now, in text, and nothing for others (Story 8.3)", () => {
    expect(seatMarkText({ holder: "ai", mark: "takeover_inactivity" })).toBe(copy.marks.takeover_inactivity);
    expect(seatMarkText({ holder: "ai", mark: null })).toBeNull();
    expect(seatMarkText({ holder: "student", mark: "takeover_inactivity" })).toBeNull();
  });

  it("gives a Student Seat its links or the line that none exists yet, and others nothing", () => {
    const [factory, distributor, wholesaler, retailer] = seatsUpstreamFirst(insight([]));
    // A kind with no words of its own yet is never shown as its code.
    expect(linkTexts(factory!)).toEqual([
      { kind: "explanation", text: copy.links.explanation, href: "/f" },
      { kind: "later_kind", text: copy.otherLink, href: "/g" },
    ]);
    expect(linkTexts(retailer!)).toBe(copy.noLinks);
    expect(linkTexts(wholesaler!)).toBeNull();
    expect(linkTexts(distributor!)).toBeNull();
  });

  it("words every mark of the one mapping, never a bare code", () => {
    const all = Object.keys(copy.marks) as SeatMark[];
    expect(all).toHaveLength(11);
    for (const mark of all) expect(markText([mark])).not.toContain("_");
    expect(markText(["takeover_inactivity", "fallback_timeout"])).toBe(
      `${copy.marks.takeover_inactivity}. ${copy.marks.fallback_timeout}`,
    );
  });

  it("prints the api's numbers formatted only, with no Order before it is placed", () => {
    expect(weekRow(week(3, { inventory: 1200, backlog: 0, cost: "6.5000", order: null, holder: "ai", name: null }))).toEqual({
      week: 3,
      playedBy: copy.aiPlayer,
      incomingOrder: "4",
      incomingDelivery: "4",
      inventory: "1 200",
      backlog: "0",
      order: "",
      cost: "6,50",
      opened: "",
      ordered: "",
      took: "",
      marks: "",
    });
  });

  it("shows when the Week opened and the Order came in Oslo time, and the time between (Story 8.1)", () => {
    // 12:58 UTC is 13:58 in Oslo in November; 2 h 10 min later the Order came.
    const row = weekRow(week(5, { opened_at: "2026-11-18T12:58:00Z", ordered_at: "2026-11-18T15:08:30Z" }));
    expect([row.opened, row.ordered, row.took]).toEqual([
      copy.at("18. nov.", "13:58"),
      copy.at("18. nov.", "16:08"),
      nb.homes.student.duration.hours(2),
    ]);
    // Across midnight in Oslo, and in summer time (UTC+2).
    expect(clockText("2026-06-30T22:30:00Z")).toBe(copy.at("1. jul.", "00:30"));
    // An Order within the minute, and one not placed yet.
    expect(weekRow(week(6, { opened_at: "2026-11-18T12:58:00Z", ordered_at: "2026-11-18T12:58:01Z" })).took).toBe(
      nb.homes.student.duration.underMinute,
    );
    const open = weekRow(week(7, { opened_at: "2026-11-18T12:58:00Z", ordered_at: null, order: null }));
    expect([open.ordered, open.took]).toEqual(["", ""]);
  });

  it("keeps the Roles in chain order and knows a game with no Week", () => {
    expect(roleTables(insight([[week(1)]])).map((t) => t.name)).toEqual([
      nb.terms.retailer,
      nb.terms.wholesaler,
      nb.terms.distributor,
      nb.terms.factory,
    ]);
    expect(hasWeeks(insight([]))).toBe(false);
    expect(hasWeeks(insight([[week(1)]]))).toBe(true);
  });
});

describe("the Spillinnsikt body", () => {
  it("shows «Spillet har ikke startet.» and the four Seats, and no table, before the start", () => {
    const html = renderToStaticMarkup(createElement(InsightBody, { data: insight([]) }));
    expect(html).toContain(copy.notStarted);
    expect(html).not.toContain("<table");
    expect(html.match(/data-role="/g)).toHaveLength(4);
  });

  it("draws one table per Role, Week rows with a sticky Uke header, marks in words", () => {
    const weeks = CHAIN.map(() => [week(1), week(2, { holder: "ai", name: null, marks: ["takeover_inactivity"], order: null })]);
    // The per-Role tables stand after the charts (Story 7.8).
    const html = renderToStaticMarkup(createElement(InsightBody, { data: insight(weeks) })).split(`>${copy.weeksTitle}<`)[1]!;
    expect(html.match(/<table/g)).toHaveLength(4);
    expect(html.match(/<th scope="row"/g)).toHaveLength(8);
    expect(html).toContain(copy.marks.takeover_inactivity);
    expect(html).toContain(copy.noOrder);
    expect(html).toContain(copy.region(nb.terms.retailer));
    expect(html.indexOf(copy.region(nb.terms.retailer))).toBeLessThan(html.indexOf(copy.region(nb.terms.factory)));
  });
});

describe("Spillinnsikt's charts (Story 7.8)", () => {
  const charts = copy.charts;
  const played = (): GameInsight => {
    const data = insight(
      CHAIN.map((_, r) => [
        week(1, { order: 4 + r, inventory: 12 - r, backlog: 0 }),
        week(2, { order: 12 + r, inventory: 0, backlog: 3 + r }),
        week(3, { order: null, inventory: 2, backlog: 0 }),
      ]),
    );
    return {
      ...data,
      demand: [1, 2, 3].map((w) => ({ week: w, demand: w === 1 ? 4 : 8 })),
      roles: data.roles.map((role) => ({ ...role, first_large_order_week: role.role === "retailer" ? null : 2 })),
    };
  };

  it("gives the Ordrestolper the four Roles Fabrikk first, then the customers, with the api's numbers only", () => {
    const rows = orderRoles(played());
    expect(rows.map((row) => row.key)).toEqual(["factory", "distributor", "wholesaler", "retailer", CUSTOMERS]);
    expect(rows.map((row) => row.name)).toEqual([nb.terms.factory, nb.terms.distributor, nb.terms.wholesaler, nb.terms.retailer, charts.orders.customers]);
    // The open Week's Order not yet placed is left out; the first large Week is the api's.
    expect(rows[0]).toEqual({ key: "factory", name: nb.terms.factory, orders: [{ week: 1, order: 7 }, { week: 2, order: 15 }], firstLargeWeek: 2 });
    expect(rows[3]!.firstLargeWeek).toBeNull();
    expect(rows[4]).toEqual({
      key: CUSTOMERS,
      name: charts.orders.customers,
      orders: [{ week: 1, order: 4 }, { week: 2, order: 8 }, { week: 3, order: 8 }],
      firstLargeWeek: null,
    });
    // No Forsterkning before Story 9.5 wires it.
    expect(rows.every((row) => !("amplification" in row))).toBe(true);
  });

  it("gives «Lager og restordre» the stored values Fabrikk first, and both tables a printed cell per Uke", () => {
    const data = played();
    expect(chartWeeks(data)).toEqual([1, 2, 3]);
    expect(stockRoles(data)[0]).toEqual({
      key: "factory",
      name: nb.terms.factory,
      weeks: [
        { week: 1, inventory: 9, backlog: 0 },
        { week: 2, inventory: 0, backlog: 6 },
        { week: 3, inventory: 2, backlog: 0 },
      ],
    });
    expect(orderTableRows(data)[0]).toEqual({ key: "factory", label: nb.terms.factory, cells: ["7", "15", ""] });
    expect(orderTableRows(data)[4]!.cells).toEqual(["4", "8", "8"]);
    const stock = stockTableRows(data);
    expect(stock).toHaveLength(8);
    expect(stock.slice(0, 2)).toEqual([
      { key: "factory:stock", label: charts.stock.stockRow(nb.terms.factory), cells: ["9", "0", "2"] },
      { key: "factory:backlog", label: charts.stock.backlogRow(nb.terms.factory), cells: ["0", "6", "0"] },
    ]);
  });

  it("puts both charts over the per-Role tables, each with «Vis som tabell», and none before the start", () => {
    const html = renderToStaticMarkup(createElement(InsightBody, { data: played() }));
    expect(html.indexOf(charts.title)).toBeLessThan(html.indexOf(copy.weeksTitle));
    expect(html).toContain('data-chart-block="orders"');
    expect(html).toContain('data-chart-block="stock"');
    expect(html.match(new RegExp(`>${charts.showTable}</button>`, "g"))).toHaveLength(2);
    expect(html.indexOf(charts.orders.title)).toBeLessThan(html.indexOf(charts.stock.title));
    // The Ordrestolper's Rolle × Uke rows: Fabrikk first, the customers last, no Forsterkning.
    const bars = html.split('data-chart-block="orders"')[1]!.split("data-chart-block")[0]!;
    expect(bars.indexOf('data-role="factory"')).toBeLessThan(bars.indexOf(`data-role="${CUSTOMERS}"`));
    expect(html).not.toContain(charts.orders.amplification);
    const before = renderToStaticMarkup(createElement(InsightBody, { data: insight([]) }));
    expect(before).not.toContain("data-insight-charts");
  });
});
