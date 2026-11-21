import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SeatStatus } from "@/components/seat-status";
import { nb } from "@/copy/nb";

import { seatRows, type StatusSeat, waitDuration, waitedFor } from "./seat-status";

const copy = nb.homes.student;
const NOW = Date.parse("2026-11-21T12:00:00Z");
const ago = (minutes: number) => new Date(NOW - minutes * 60_000).toISOString();

const seat = (over: Partial<StatusSeat>): StatusSeat => ({
  role: "factory",
  holder: "student",
  name: "Jonas",
  mine: false,
  ordered: false,
  wait_started_at: null,
  mark: null,
  ...over,
});

const GAME: StatusSeat[] = [
  seat({ role: "factory", holder: "ai", name: null, ordered: false }),
  seat({ role: "distributor", name: "Jonas", wait_started_at: ago(3.5) }),
  seat({ role: "wholesaler", name: "Sara", mine: true, wait_started_at: ago(3.5) }),
  seat({ role: "retailer", name: "Noah", ordered: true }),
];

describe("Setestatus words (Story 6.14)", () => {
  it("counts the wait down to whole units", () => {
    expect(waitDuration(59_999)).toBe("under 1 min");
    expect(waitDuration(3 * 60_000 + 59_000)).toBe("3 min");
    expect(waitDuration(59 * 60_000)).toBe("59 min");
    expect(waitDuration(60 * 60_000)).toBe("1 t");
    expect(waitDuration(47 * 3_600_000)).toBe("47 t");
    expect(waitDuration(50 * 3_600_000)).toBe("2 d");
  });

  it("says each Seat's state in words: ordered, waited for with the wait, the AI and the viewer", () => {
    const rows = seatRows(GAME, NOW);
    expect(rows.map((row) => [row.role, row.holder, row.state, row.status])).toEqual([
      ["Fabrikk", "KI-spiller", "waiting", "venter"],
      ["Distributør", "Jonas", "waiting", "venter, 3 min"],
      ["Grossist", "Sara (deg)", "waiting", "venter"],
      ["Detaljist", "Noah", "ordered", "har bestilt"],
    ]);
  });

  it("before any Student has ordered a waiting Seat has no duration", () => {
    const [row] = seatRows([seat({ wait_started_at: null })], NOW);
    expect(row.status).toBe(copy.status.waiting);
  });

  it("tells no state for a game that does not run", () => {
    const [row] = seatRows([seat({ ordered: null })], NOW);
    expect([row.state, row.status]).toEqual([null, null]);
  });

  it("names a Seat the Play guard switched as a rule-based KI-spiller", () => {
    const [row] = seatRows([seat({ holder: "ai", name: null, ordered: true, mark: "guard_switch" })], NOW);
    expect(row.holder).toBe("KI-spiller (regelbasert)");
  });

  it("names whom the game waits for, by name or Role, the viewer last as «deg»", () => {
    expect(waitedFor(GAME, NOW)).toBe("Fabrikk, Jonas (3 min) og deg");
    expect(copy.waitingOn(waitedFor(GAME, NOW)!)).toBe("Venter på: Fabrikk, Jonas (3 min) og deg.");
    // The Confirmed message names only the others.
    expect(waitedFor(GAME, NOW, true)).toBe("Fabrikk og Jonas (3 min)");
    // A Student whose name cannot be shown is named by Role.
    expect(waitedFor([seat({ role: "retailer", name: null, wait_started_at: ago(5) })], NOW)).toBe("Detaljist (5 min)");
    expect(waitedFor([seat({ ordered: true })], NOW)).toBeNull();
  });
});

describe("SeatStatus", () => {
  /** The text of each row, tags dropped. */
  const rowTexts = (html: string) =>
    [...html.matchAll(/<li[^>]*>(.*?)<\/li>/g)].map(([, inner]) => inner.replace(/<[^>]+>/g, ""));

  it("states every row in text, with the dot decorative and the announcement for screen readers", () => {
    const html = renderToStaticMarkup(
      <SeatStatus title="Setene" titleId="s" rows={seatRows(GAME, NOW)} announcement="Venter på: Jonas (3 min) og deg." />,
    );
    expect(html).toContain('aria-labelledby="s"');
    expect(html).toContain('<h2 id="s"');
    expect(rowTexts(html)).toEqual([
      "FabrikkKI-spillerventer",
      "DistributørJonasventer, 3 min",
      "GrossistSara (deg)venter",
      "DetaljistNoahhar bestilt",
    ]);
    expect(html.match(/<svg aria-hidden="true"/g)).toHaveLength(4);
    expect(html.match(/data-state="(\w+)"/g)).toEqual([
      'data-state="waiting"',
      'data-state="waiting"',
      'data-state="waiting"',
      'data-state="ordered"',
    ]);
    expect(html).toMatch(/aria-live="polite"[^>]*>Venter på: Jonas \(3 min\) og deg\.</);
  });

  it("draws no dot or status for rows without a state, and a level-4 heading on Hjem", () => {
    const html = renderToStaticMarkup(
      <SeatStatus title="Setene" titleId="s" level={4} rows={seatRows([seat({ ordered: null })], NOW)} />,
    );
    expect(html).not.toContain("<svg");
    expect(rowTexts(html)).toEqual(["FabrikkJonas"]);
    expect(html).toContain('<h4 id="s"');
  });
});
