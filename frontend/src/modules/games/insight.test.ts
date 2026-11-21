import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameInsight, InsightWeek, SeatMark } from "./api";
import { hasWeeks, holderText, linkTexts, markText, roleTables, seatsUpstreamFirst, weekRow } from "./insight";
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
  demand: [],
  seats: [
    { role: "retailer", holder: "student", name: "Ida Berg", links: [] },
    { role: "wholesaler", holder: "ai", name: null, links: [] },
    { role: "distributor", holder: "free", name: null, links: [] },
    {
      role: "factory",
      holder: "student",
      name: null,
      links: [
        { kind: "explanation", href: "/f" },
        { kind: "later_kind", href: "/g" },
      ],
    },
  ],
  roles: CHAIN.map((role, i) => ({ role, weeks: weeks[i] ?? [] })),
});

describe("Spillinnsikt's words (Story 7.7)", () => {
  it("puts the Seats upstream first and names each holder", () => {
    const seats = seatsUpstreamFirst(insight([]));
    expect(seats.map((s) => s.role)).toEqual(["factory", "distributor", "wholesaler", "retailer"]);
    expect(seats.map(holderText)).toEqual([copy.unknownStudent, copy.freeSeat, copy.aiPlayer, "Ida Berg"]);
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
      marks: "",
    });
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
    const html = renderToStaticMarkup(createElement(InsightBody, { data: insight(weeks) }));
    expect(html.match(/<table/g)).toHaveLength(4);
    expect(html.match(/<th scope="row"/g)).toHaveLength(8);
    expect(html).toContain(copy.marks.takeover_inactivity);
    expect(html).toContain(copy.noOrder);
    expect(html).toContain(copy.region(nb.terms.retailer));
    expect(html.indexOf(copy.region(nb.terms.retailer))).toBeLessThan(html.indexOf(copy.region(nb.terms.factory)));
  });
});
