import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import type { GameInsight, InsightSeat } from "@/modules/games/api";
import { Spillstyring } from "@/modules/games/spillstyring";

import { checkShare, FACTOR_OPTIONS, factorChoice, factorText, ownLines, percentText, summaryText } from "./adjustment";
import { AdjustmentBlock } from "./adjustment-block";
import type { StudentPage } from "./api";

/** Tilrettelegging (Story 8.9, FR-17, UX-DR52, UX-DR53): the block's lines, the form's rule, the
 * Student's own Hjem lines and the Lecturer's Spillstyring line. */
const copy = nb.reports.adjustment;

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

const page = (over: Partial<StudentPage> = {}): StudentPage => ({
  class_session_id: "s1",
  class_id: "c1",
  class_name: "Klasse",
  session_number: 1,
  user_id: "u-jonas",
  name: "Jonas",
  class_share: 80,
  adjustment: null,
  ...over,
});

describe("Tilrettelegging's words", () => {
  it("writes factors and shares the Norwegian way, with no-break spaces", () => {
    expect(factorText(2)).toBe("2 ×");
    expect(factorText(1.5)).toBe("1,5 ×");
    expect(percentText(60)).toBe("60 %");
    expect(FACTOR_OPTIONS.map((option) => option.label)).toEqual([copy.asClass, "1,5 ×", "2 ×", "3 ×"]);
  });

  it("sums up only what applies", () => {
    expect(summaryText(null)).toBe("Ingen tilrettelegging.");
    expect(summaryText({ time_factor: 2, share_percent: 60 })).toBe("Mer tid: 2 ×. Andel uker: 60 %.");
    expect(summaryText({ time_factor: 1.5, share_percent: null })).toBe("Mer tid: 1,5 ×.");
    expect(summaryText({ time_factor: 1, share_percent: 0 })).toBe("Andel uker: 0 %.");
  });

  it("takes a whole share from 0 to the class share", () => {
    expect(checkShare("60", 80)).toEqual({ share: 60 });
    expect(checkShare(" 0 ", 80)).toEqual({ share: 0 });
    expect(checkShare("80 %", 80)).toEqual({ share: 80 });
    for (const text of ["81", "-1", "60,5", "", "seks"]) {
      expect(checkShare(text, 80)).toEqual({ error: "Skriv et helt tall fra 0 til 80." });
    }
  });

  it("opens the form on the stored factor", () => {
    expect(factorChoice(2)).toBe("2");
    expect(factorChoice(1.5)).toBe("1.5");
    expect(factorChoice(undefined)).toBe("1");
  });

  it("gives the Student their own lines only for what is adjusted", () => {
    expect(ownLines({ time_factor: 2, share_percent: 60 })).toEqual([
      "Du har mer tid før en KI-spiller tar setet ditt (2 × vanlig ventetid).",
      "For deg er kravet 60 % av ukene.",
    ]);
    expect(ownLines({ time_factor: null, share_percent: 50 })).toEqual(["For deg er kravet 50 % av ukene."]);
    expect(ownLines(null)).toEqual([]);
  });
});

describe("The block «Tilrettelegging»", () => {
  it("reads «Ingen tilrettelegging.» or the summary, with «Endre tilrettelegging»", () => {
    const none = html(<AdjustmentBlock data={page()} />);
    expect(none).toContain(copy.title);
    expect(none).toContain("Ingen tilrettelegging.");
    expect(none).toContain(copy.change);
    expect(none).not.toContain("data-adjustment-form");
    const some = html(<AdjustmentBlock data={page({ adjustment: { time_factor: 2, share_percent: 60 } })} />);
    expect(some).toContain("Mer tid: 2 ×. Andel uker: 60 %.");
  });
});

describe("Spillstyring's Tilrettelegging line", () => {
  const seat = (extra: boolean): InsightSeat => ({
    role: "factory",
    holder: "student",
    name: "Jonas",
    user_id: "u-jonas",
    links: [],
    mark: null,
    mark_by: null,
    takeover: "this_week",
    extra_time: extra,
  });
  const insight = (extra: boolean): GameInsight => ({
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
    seats: [seat(extra)],
    roles: [],
    can_pause: false,
    can_adjust: false,
    can_start: false,
    can_mark_in_room: false,
  });

  it("adds «Jonas har tilrettelegging med mer tid.» only where the api marks the Seat", () => {
    expect(html(<Spillstyring data={insight(true)} />)).toContain("Jonas har tilrettelegging med mer tid.");
    expect(html(<Spillstyring data={insight(false)} />)).not.toContain("tilrettelegging");
  });
});
