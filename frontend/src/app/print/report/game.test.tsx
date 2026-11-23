import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SeatState } from "@/modules/games/api";
import week11 from "@/modules/games/fixtures/play-week-11.json";

import { reportCopy } from "./copy";
import { type GameData, holderRuns, inWeeks, largestOrder, markLines, stockMost, weekBlocks } from "./game";
import { Report } from "./report";
import type { ReportData } from "./sections";

const SEAT = week11.seat_state as SeatState;
const ROLES = ["retailer", "wholesaler", "distributor", "factory"] as const;

/** A finished game of 11 Uker: the Student the Grossist; the Detaljist a Student, then an AI
 * player after a Takeover in Uke 6; the other two AI players. */
function game(over: Partial<GameData> = {}, n = 11): GameData {
  return {
    makeup: false,
    game_number: 3,
    role: "wholesaler",
    weeks_played: 11,
    weeks_total: 11,
    finished: true,
    total_cost: "123.50",
    seat: SEAT,
    last_order: 7,
    demand: Array.from({ length: n }, (_, i) => ({ week: i + 1, demand: i < 4 ? 4 : 8 })),
    roles: ROLES.map((role, r) => ({
      role,
      first_large_order_week: role === "factory" ? 9 : null,
      weeks: Array.from({ length: n }, (_, i) => {
        const week = i + 1;
        const student = role === "wholesaler" || (role === "retailer" && week < 6);
        return {
          week,
          order: week + r,
          inventory: r * 2 + (week % 3),
          backlog: week > 7 ? week - 7 + r : 0,
          holder: student ? ("student" as const) : ("ai" as const),
          marks: role === "retailer" && week === 6 ? ["takeover_inactivity" as const] : [],
        };
      }),
    })),
    ...over,
  };
}

function report(section: ReportData["sections"][number]): string {
  const data: ReportData = {
    schema_version: 1,
    generated_at: "2026-12-11T09:05:00Z",
    student_name: "Sara Nilsen",
    class_name: "IBE160 høst",
    session_number: 2,
    dates: { start_at: null, play_deadline: null, debrief_deadline: null, test_deadline: null },
    sections: [section],
  };
  return renderToStaticMarkup(<Report data={data} />);
}

describe("the report's game section", () => {
  it("cuts the Uker into as few even blocks as A4 holds", () => {
    const weeks = (n: number) => Array.from({ length: n }, (_, i) => i + 1);
    expect(weekBlocks(weeks(11))).toEqual([{ from: 1, to: 11 }]);
    expect(weekBlocks(weeks(18))).toEqual([{ from: 1, to: 18 }]);
    expect(weekBlocks(weeks(20))).toEqual([
      { from: 1, to: 10 },
      { from: 11, to: 20 },
    ]);
    expect(weekBlocks(weeks(36))).toEqual([
      { from: 1, to: 18 },
      { from: 19, to: 36 },
    ]);
    expect(weekBlocks([])).toEqual([]);
  });

  it("gives every block the game's one scale", () => {
    const chain = game();
    expect(largestOrder(chain)).toBe(14);
    expect(largestOrder(inWeeks(chain, 1, 2))).toBe(5);
    expect(stockMost(chain)).toEqual({ stock: 8, backlog: 7 });
    expect(inWeeks(chain, 3, 4).demand.map((week) => week.week)).toEqual([3, 4]);
  });

  it("words who played each Role by runs of Uker, and each mark of the one mapping", () => {
    const retailer = game().roles[0]!;
    expect(holderRuns(retailer)).toEqual(["Student, Uke 1–5", "KI-spiller, Uke 6–11"]);
    expect(markLines(retailer)).toEqual(["Uke 6: KI tok over etter ventetiden."]);
    expect(holderRuns({ weeks: [{ ...retailer.weeks[0]!, holder: "free" }] })).toEqual(["Ledig, Uke 1"]);
  });

  it("renders the Seat over its table and both chain charts, each with a title and its table", () => {
    const html = report({ kind: "game", game: game() });
    expect(html).toContain(`>${reportCopy.game.classGame}</h2>`);
    expect(html).toMatch(/Spill<\/dt><dd>3<\/dd>/);
    expect(html).toContain("11 av 11");
    expect(html).toContain("123,50 kr");
    // Graf over tabell for the Seat: no nå, no Uker ahead, the last Uke's Order a plain number.
    const seat = html.slice(html.indexOf('data-block="seat"'), html.indexOf('data-block="orders"'));
    expect(seat).toContain('data-chart="net"');
    expect(seat).not.toContain("data-now");
    expect(seat).not.toContain(">Nå<");
    expect(seat.match(/data-col="\d+"/g)).toHaveLength(11);
    expect(seat).toContain('data-row="order"');
    // The chain: Ordrestolper with the own Role marked and Kundene, «Lager og restordre» with its rows.
    expect(html).toContain("Grossist (deg)");
    expect(html).toContain("Kundene");
    expect(html).toContain('data-row="factory:stock"');
    expect(html).toContain('data-row="retailer:backlog"');
    // Every chart SVG carries its title.
    const svgs = html.match(/<svg[^>]*>/g) ?? [];
    const titles = html.match(/<svg[^>]*><title>/g) ?? [];
    expect(svgs.length).toBeGreaterThan(4);
    expect(titles).toHaveLength(svgs.length);
    // Who played: by Role only, the mark in words.
    expect(html).toContain("Student, Uke 1–5. KI-spiller, Uke 6–11.");
    expect(html).toContain("Uke 6: KI tok over etter ventetiden.");
    expect(html).not.toContain("Sara Nilsen</td>");
  });

  it("is headed «Oppfølgingsspill» for a make-up, which has no game number", () => {
    const html = report({ kind: "game", game: game({ makeup: true, game_number: null }) });
    expect(html).toContain(`>${reportCopy.game.makeup}</h2>`);
    expect(html).not.toMatch(/Spill<\/dt>/);
  });

  it("says so when the Student has no game, and when it did not run to its end", () => {
    expect(report({ kind: "game", game: null })).toContain(reportCopy.game.none);
    expect(report({ kind: "game", game: game({ finished: false }) })).toContain(reportCopy.game.notFinished);
  });

  it("draws a long game in two blocks of each chart", () => {
    const html = report({ kind: "game", game: game({}, 20) });
    // The chain's 20 Uker in two blocks of 10; the fixture's Seat stands in Uke 11: one block.
    expect(html.match(/data-block="orders"/g)).toHaveLength(2);
    expect(html.match(/data-block="stock"/g)).toHaveLength(2);
    expect(html.match(/data-block="seat"/g)).toHaveLength(1);
  });
});
