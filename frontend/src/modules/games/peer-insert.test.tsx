import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { absentName, conflictText, insertLine } from "./peer-insert";
import type { StatusSeat } from "./seat-status";
import { GameSeatStatus } from "./seat-status-view";

const copy = nb.homes.student.insert;
const NOW = Date.parse("2026-11-24T12:00:00Z");

const seat = (over: Partial<StatusSeat>): StatusSeat => ({
  role: "factory",
  holder: "student",
  name: "Jonas",
  mine: false,
  ordered: false,
  wait_started_at: null,
  mark: null,
  taken_over: false,
  ordering_for: null,
  guard_switched: false,
  reclaim_queued: false,
  can_insert: false,
  insert_agreed: false,
  ...over,
});

/** Thursday 26 November 2026, 19:00 in Oslo (18:00 UTC). */
const THURSDAY_19 = "2026-11-26T18:00:00Z";

function render(seats: StatusSeat[]): string {
  return renderToStaticMarkup(
    <QueryClientProvider client={new QueryClient()}>
      <GameSeatStatus gameId="g" seats={seats} now={NOW} titleId="s" />
    </QueryClientProvider>,
  );
}

describe("Sett inn KI-spiller (Story 8.8, FR-89, UX-DR27)", () => {
  it("states the Seat's own insert time, or the agreed time, and never why", () => {
    expect(insertLine(seat({ insert_at: THURSDAY_19 }))).toBe(
      "Etter to. 19:00 kan dere sette inn en KI-spiller.",
    );
    expect(insertLine(seat({ insert_at: THURSDAY_19, insert_agreed: true }))).toBe(
      "Avtalt tid to. 19:00. Etter det kan dere sette inn en KI-spiller.",
    );
    expect(insertLine(seat({}))).toBeNull();
    // No reason a Seat's time differs: no factor, no Tilrettelegging, no «mer tid».
    for (const line of [copy.after("x"), copy.agreed("x")]) expect(line).not.toMatch(/tilrette|mer tid|×/i);
  });

  it("shows the consequence directly above «Sett inn KI-spiller for Jonas» only when the api allows it", () => {
    const html = render([seat({ can_insert: true }), seat({ role: "retailer", name: "Sara", mine: true })]);
    const consequence = html.indexOf(nb.spillstyring.thisWeek("Jonas"));
    const button = html.indexOf(nb.spillstyring.takeover("Jonas"));
    expect(consequence).toBeGreaterThan(-1);
    expect(button).toBeGreaterThan(consequence);
    expect(html.match(/<button/g)).toHaveLength(1);
    expect(html).toContain("w-full lg:w-auto");
    // Not allowed: no control, the before line instead.
    const before = render([seat({ insert_at: THURSDAY_19 })]);
    expect(before).not.toContain("<button");
    expect(before).toContain("Etter to. 19:00 kan dere sette inn en KI-spiller.");
  });

  it("names the Student by Role when no name can be shown", () => {
    expect(absentName(seat({ name: null }))).toBe("Fabrikk");
  });

  it("names who came first: a Student by name, the Lecturer, or the automatic Takeover", () => {
    expect(conflictText("student", "Sara")).toBe("Sara har allerede satt inn en KI-spiller.");
    expect(conflictText("staff", null)).toBe(copy.takenByStaff);
    expect(conflictText("system", null)).toBe(nb.spillstyring.takenBySystem);
    expect(conflictText("student", null)).toBe(nb.spillstyring.takenByUnknown);
  });
});
