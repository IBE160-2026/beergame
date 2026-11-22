import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { actionErrorMessage } from "@/lib/api/mutation";
import { overviewStartedPath, startGamesPath } from "@/modules/identity/homes";

import type { GameInsight } from "./api";
import { Spillstyring } from "./spillstyring";
import {
  confirmText,
  startedFirst,
  startedParam,
  startedText,
  startLinkText,
  startResultText,
} from "./start-games";

/** «Start spillet» and «Start spill» (Story 8.10, FR-22, UX-DR52): the api decides which games may
 * start and who started one first; the page words it. */
const copy = nb.spillstyring.start;

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
    status: "not_started",
    version: 1,
    weeks_total: 20,
    demand: [],
    seats: [],
    roles: [],
    can_pause: false,
    can_adjust: false,
    can_start: true,
    can_mark_in_room: false,
    ...over,
  };
}

describe("«Start spillet» in Spillstyring", () => {
  it("shows the consequence directly above the one primary button, full width below 1024 px", () => {
    const page = html(<Spillstyring data={insight({})} />);
    expect(page).toContain(`>${nb.spillstyring.title}</h2>`);
    expect(copy.consequence).toBe("Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.");
    expect(page.indexOf(copy.consequence)).toBeLessThan(page.indexOf(">Start spillet<"));
    const button = page.match(/<button[^>]*data-start-game=""[^>]*>/)?.[0] ?? "";
    expect(button).toContain("w-full lg:w-auto");
    expect(button).toMatch(/aria-describedby="[^"]+"/);
    expect([...page.matchAll(/<button/g)]).toHaveLength(1);
  });

  it("offers nothing to an Assistant lecturer, before the lock, or once the game runs", () => {
    expect(html(<Spillstyring data={insight({ can_start: false })} />)).toBe("");
    const running = html(<Spillstyring data={insight({ status: "running", can_start: false, can_pause: true })} />);
    expect(running).not.toContain("Start spillet");
  });

  it("words the result, and who started it first by the name the view read again gives", () => {
    expect(startResultText({ kind: "done" }, "Sara")).toBe("Spillet er startet.");
    expect(startResultText({ kind: "first" }, "Sara")).toBe("Spillet ble startet av Sara.");
    expect(startResultText({ kind: "first" }, null)).toBe(copy.startedAlready);
    const first = new ApiRequestError(409, "game_already_started", {
      acted_by: { kind: "student", user_id: "u1" },
      acted_at: "2026-11-22T08:00:00Z",
    });
    expect(startedFirst(first)).toBe(true);
    expect(startedFirst(new ApiRequestError(409, "game_not_ready"))).toBe(false);
    const said = (code: string) => actionErrorMessage(new ApiRequestError(409, code), copy.refusals, copy.failed);
    expect(said("game_not_ready")).toBe(copy.refusals.game_not_ready);
    expect(said("network_error")).toBe(copy.failed);
  });
});

describe("«Start spill» for every game not started", () => {
  it("names the Lenke with the real count, and none with 0", () => {
    expect(startLinkText(12)).toBe("Start spill som ikke har startet (12)");
    expect(startLinkText(0)).toBeNull();
    expect(startLinkText(undefined)).toBeNull();
    expect(confirmText(12)).toBe("Start 12 spill");
    expect(nb.overview.start.consequence).toBe("Spillene starter for alle i dem. Reglene for ventetid gjelder fra nå.");
  });

  it("carries the real count back to the Oversikt once, and reads only a whole number", () => {
    expect(startGamesPath("s1")).toBe("/klasseokter/s1/oversikt/start");
    expect(overviewStartedPath("s1", 12)).toBe("/klasseokter/s1/oversikt?startet=12");
    expect(startedParam(new URLSearchParams("startet=12"))).toBe(12);
    expect(startedParam(new URLSearchParams("startet=0"))).toBe(0);
    for (const bad of ["", "startet=", "startet=-1", "startet=1.5", "startet=abc", "startet=99999"]) {
      expect(startedParam(new URLSearchParams(bad))).toBeNull();
    }
    expect(startedText(12)).toBe("12 spill er startet.");
  });
});
