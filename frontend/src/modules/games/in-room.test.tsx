import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameInsight, OverviewGame } from "./api";
import { confirmLabel, inRoomError, inRoomLine, inRoomMinutes, markedText } from "./in-room";
import { InRoomLine } from "./in-room-view";
import { rowLabel, tableRows, wallGroups } from "./overview";
import { Spillstyring } from "./spillstyring";

/** «I rommet» (Story 8.11, FR-36, UX-DR52, UX-DR62): the api says whether a Labtime is on, until
 * when the mark holds and each Student's own minutes; the page words it. */
const copy = nb.spillstyring.inRoom;
// 15:00 UTC is 16:00 in Oslo in November.
const UNTIL = "2026-11-24T15:00:00Z";

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

function insight(over: Partial<GameInsight>): GameInsight {
  return {
    game_id: "g1",
    class_session_id: "s1",
    class_id: "c1",
    class_name: "Klasse",
    session_number: 1,
    game_number: 2,
    status: "running",
    version: 1,
    weeks_total: 20,
    demand: [],
    seats: [],
    roles: [],
    can_pause: false,
    can_adjust: false,
    can_start: false,
    can_mark_in_room: true,
    ...over,
  };
}

describe("the in-room limit field", () => {
  it("takes a whole number of minutes from 2 to 120 and nothing else", () => {
    expect(inRoomMinutes("10")).toBe(10);
    expect(inRoomMinutes(" 2 ")).toBe(2);
    expect(inRoomMinutes("120")).toBe(120);
    for (const wrong of ["", "1", "121", "7.5", "7,5", "-5", "ti"]) expect(inRoomMinutes(wrong)).toBeNull();
    expect(inRoomError("1")).toBe("Skriv et helt antall minutter fra 2 til 120.");
    expect(inRoomError("10")).toBeUndefined();
  });

  it("names the minutes on the primary while the value is valid", () => {
    expect(confirmLabel("10")).toBe("Marker som i rommet, 10 min");
    expect(confirmLabel("200")).toBe("Marker som i rommet");
  });
});

describe("«I rommet» in Spillstyring", () => {
  it("offers «Marker som i rommet» while a Labtime is on", () => {
    const page = html(<Spillstyring data={insight({ lab_hour_ends_at: UNTIL })} />);
    const button = page.match(/<button[^>]*data-in-room-open=""[^>]*>/)?.[0] ?? "";
    expect(button).not.toContain('aria-disabled="true"');
    expect(button).toContain("w-full lg:w-auto");
    expect(page).not.toContain(copy.onlyInLabHour);
  });

  it("shows it unavailable with its reason outside every Labtime", () => {
    const page = html(<Spillstyring data={insight({ lab_hour_ends_at: null })} />);
    const button = page.match(/<button[^>]*data-in-room-open=""[^>]*>/)?.[0] ?? "";
    expect(button).toContain('aria-disabled="true"');
    const reason = page.match(/<p id="([^"]+)"[^>]*data-in-room-unavailable=""[^>]*>Kan bare brukes i en Labtime.<\/p>/);
    expect(reason).not.toBeNull();
    expect(button).toContain(`aria-describedby="${reason?.[1]}"`);
    expect(page.indexOf(copy.onlyInLabHour)).toBeLessThan(page.indexOf("data-in-room-open"));
  });

  it("reads the mark with «Ikke i rommet lenger» once marked", () => {
    const marked = { until: UNTIL, minutes: 10 };
    expect(markedText(marked)).toBe("I rommet til 16:00. KI tar over etter 10 min uten ordre.");
    const page = html(<Spillstyring data={insight({ in_room: marked })} />);
    expect(page).toContain(markedText(marked));
    expect(page).toContain(`>${copy.end}</button>`);
    expect(page).not.toContain("data-in-room-open");
  });

  it("offers nothing to an Assistant lecturer or on a game that does not run", () => {
    expect(html(<Spillstyring data={insight({ can_mark_in_room: false, lab_hour_ends_at: UNTIL })} />)).toBe("");
    expect(html(<Spillstyring data={insight({ status: "finished", lab_hour_ends_at: UNTIL })} />)).toBe("");
  });
});

describe("the Student's «I rommet» line", () => {
  it("reads the end and the reader's own minutes", () => {
    expect(inRoomLine({ until: UNTIL, minutes: 10 })).toBe(
      "I rommet til kl. 16:00. En KI-spiller tar setet etter 10 min uten ordre.",
    );
    expect(inRoomLine({ until: UNTIL, minutes: 20 })).toContain("etter 20 min");
    expect(inRoomLine(null)).toBe("");
  });

  it("is a polite live region that is there before the line is", () => {
    const page = html(<InRoomLine inRoom={{ until: UNTIL, minutes: 10 }} />);
    expect(page).toContain('aria-live="polite"');
    // Filled after it is drawn, so the line is announced (not in the server's first draw).
    expect(page).toContain('data-in-room-line=""');
  });
});

describe("the wall's row label", () => {
  const game = {
    game_id: "g3",
    game_number: 3,
    status: "running",
    week: 4,
    version: 1,
    chain_cost: "120",
    wait_started_at: null,
    waiting_for: [],
    seats: [],
    in_room_until: UNTIL,
  } as OverviewGame;

  it("carries «I rommet» while the game is marked", () => {
    expect(rowLabel(game)).toBe("Spill 3 · I rommet");
    expect(rowLabel({ ...game, in_room_until: null })).toBe("Spill 3");
  });

  it("is the label of the game's row on the wall and in «Vis som tabell»", () => {
    const groups = [{ name: "running" as const, title: "Pågår", games: [game] }];
    expect(wallGroups(groups, new Map(), "retailer", 0)[0]!.rows[0]!.label).toBe("Spill 3 · I rommet");
    expect(tableRows(groups, new Map(), "retailer", 0)[0]!.label).toBe("Spill 3 · I rommet");
  });
});
