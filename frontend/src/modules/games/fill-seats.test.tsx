import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { fillSeatsPath, overviewFilledPath } from "@/modules/identity/homes";

import type { GameInsight } from "./api";
import {
  fillFailed,
  filledParam,
  filledText,
  fillLinkText,
  leftOutText,
  namesText,
  waitingSeatText,
} from "./fill-seats";
import { Spillstyring } from "./spillstyring";

/** «Sett inn KI-spiller i alle seter som blir ventet på» (Story 8.12, FR-37, UX-DR52): the api
 * lists the Seats and leaves out those with Tilrettelegging; the page words them. */
const copy = nb.spillstyring.fill;
const page = nb.overview.fill;

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
    status: "waiting",
    version: 1,
    weeks_total: 20,
    demand: [],
    seats: [],
    roles: [],
    can_pause: false,
    can_adjust: false,
    can_start: false,
    can_mark_in_room: false,
    waited_for: [],
    left_out: [],
    ...over,
  };
}

const NOAH = { seat_id: "a", role: "wholesaler" as const, name: "Noah" };
const EMMA = { seat_id: "b", role: "factory" as const, name: "Emma" };
const JONAS = { seat_id: "c", role: "retailer" as const, name: "Jonas" };

describe("the helpers", () => {
  it("words the Lenke, the result lines and the left-out line with the real counts", () => {
    expect(fillLinkText(9)).toBe("Sett inn KI-spiller i alle seter som blir ventet på (9)");
    expect(fillLinkText(0)).toBeNull();
    expect(fillLinkText(undefined)).toBeNull();
    expect(filledText(2)).toBe("2 KI-spillere satt inn.");
    expect(filledText(1)).toBe("1 KI-spiller satt inn.");
    expect(filledText(0)).toBe(copy.none);
    expect(page.done(9)).toBe("9 KI-spillere er satt inn.");
    expect(page.done(1)).toBe("1 KI-spiller er satt inn.");
    expect(page.confirm(9)).toBe("Sett inn 9 KI-spillere");
    expect(page.confirm(1)).toBe("Sett inn 1 KI-spiller");
    expect(leftOutText([JONAS])).toBe("Ikke med (tilrettelegging): Jonas");
    expect(leftOutText([])).toBeNull();
    expect(namesText(["Noah", "Emma", "Jonas"])).toBe("Noah, Emma og Jonas");
    // A Student no longer named in the Class is named by Role.
    expect(leftOutText([{ ...JONAS, name: null }])).toBe("Ikke med (tilrettelegging): Detaljist");
  });

  it("says each Seat with its wait on the server's clock: «Noah, 23 t»", () => {
    const since = "2026-11-21T09:00:00Z";
    const now = Date.parse(since) + 23 * 3600_000 + 59_000;
    expect(waitingSeatText({ ...NOAH, since }, now)).toBe(`Noah, ${nb.homes.student.duration.hours(23)}`);
  });

  it("reads the count carried back to the Oversikt, and nothing from a hand-typed address", () => {
    expect(overviewFilledPath("s1", 9)).toMatch(/\/oversikt\?satt-inn=9$/);
    expect(fillSeatsPath("s1")).toMatch(/\/oversikt\/sett-inn$/);
    expect(filledParam(new URLSearchParams("satt-inn=9"))).toBe(9);
    expect(filledParam(new URLSearchParams("satt-inn=ni"))).toBeNull();
    expect(filledParam(new URLSearchParams(""))).toBeNull();
  });
});

describe("the per-game button in Spillstyring", () => {
  it("shows the consequence directly above the secondary button, then the Seats left out", () => {
    const shown = html(<Spillstyring data={insight({ waited_for: [NOAH, EMMA], left_out: [JONAS] })} />);
    const consequence = copy.consequence("Noah og Emma");
    expect(shown).toContain(consequence);
    const button = shown.match(/<button[^>]*data-fill-seats=""[^>]*>[^<]*/)?.[0] ?? "";
    expect(button).toContain(">Sett inn KI-spiller i alle seter som blir ventet på (2)");
    expect(button).toContain("w-full lg:w-auto");
    expect(button).not.toContain("primary");
    expect(shown.indexOf(consequence)).toBeLessThan(shown.indexOf("data-fill-seats=\"\""));
    expect(shown.indexOf("data-fill-seats=\"\"")).toBeLessThan(shown.indexOf("Ikke med (tilrettelegging): Jonas"));
  });

  it("shows only the left-out line when every waited-for Seat has Tilrettelegging", () => {
    const shown = html(<Spillstyring data={insight({ left_out: [JONAS] })} />);
    expect(shown).toContain("Ikke med (tilrettelegging): Jonas");
    expect(shown).not.toContain("data-fill-seats=\"\"");
  });

  it("is not there when the game waits for no one, or for an Assistant lecturer (the api lists none)", () => {
    expect(html(<Spillstyring data={insight({})} />)).toBe("");
  });
});

describe("a fill that put no one in", () => {
  it("is a failure when a Seat failed, and a result when every Seat had ordered or been taken", () => {
    const failed = { seat_id: "a", reason: "failed" };
    const ordered = { seat_id: "b", reason: "order_exists" };
    expect(fillFailed({ inserted: 0, skipped: [failed, ordered] })).toBe(true);
    expect(fillFailed({ inserted: 0, skipped: [ordered] })).toBe(false);
    expect(fillFailed({ inserted: 1, skipped: [failed] })).toBe(false);
  });
});
