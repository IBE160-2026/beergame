import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { actionErrorMessage } from "@/lib/api/mutation";

import type { GameInsight, InsightSeat } from "./api";
import { markWords, seatMarkText } from "./insight";
import { seatMarks, seatTexts } from "./overview";
import { markBy, OverviewBand } from "./overview-band";
import { actedKind, consequenceText, resultText, Spillstyring, takenText } from "./spillstyring";

/** Spillstyring and the Varselbånd's «Sett inn KI-spiller» (Story 8.5, FR-37, UX-DR52): the api
 * decides which Seats and from when; the page words it. */
const copy = nb.spillstyring;

function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

const seat = (over: Partial<InsightSeat>): InsightSeat => ({
  role: "factory",
  holder: "student",
  name: "Jonas",
  user_id: "u-jonas",
  links: [],
  mark: null,
  mark_by: null,
  takeover: "this_week",
  ...over,
});

function insight(status: GameInsight["status"], seats: InsightSeat[]): GameInsight {
  return {
    game_id: "g1",
    class_session_id: "s1",
    class_id: "c1",
    class_name: "Klasse",
    session_number: 1,
    game_number: 2,
    status,
    version: 1,
    weeks_total: 20,
    demand: [],
    seats,
    roles: [],
    can_pause: false,
  };
}

const SEATS = [
  seat({ role: "retailer", name: "Sara", takeover: "next_week" }),
  seat({ role: "wholesaler", holder: "ai", name: null, user_id: null, takeover: null }),
  seat({ role: "distributor", holder: "ai", name: null, user_id: null, mark: "takeover_staff", mark_by: "Bård", takeover: null }),
  seat({ role: "factory", name: "Jonas" }),
];

describe("Spillstyring", () => {
  it("words the consequence from this Uke or the next, as the epic writes it", () => {
    expect(consequenceText("this_week", "Jonas")).toBe(
      "KI-spilleren bestiller for Jonas fra denne Uka. Jonas kan ta setet tilbake fra neste Uke.",
    );
    expect(consequenceText("next_week", "Jonas")).toBe("KI-spilleren bestiller for Jonas fra neste Uke.");
    expect(copy.takeover("Jonas")).toBe("Sett inn KI-spiller for Jonas");
    expect(resultText({ kind: "done", name: "Jonas" }, null)).toBe("KI-spiller satt inn for Jonas.");
  });

  it("draws one row per Seat the api offers, Fabrikk first, each consequence directly above its button", () => {
    const page = html(<Spillstyring data={insight("waiting", SEATS)} />);
    expect(page).toContain(`>${copy.title}</h2>`);
    const rows = [...page.matchAll(/data-role="(\w+)"/g)].map((m) => m[1]);
    expect(rows).toEqual(["factory", "retailer"]);
    const factory = page.slice(page.indexOf('data-role="factory"'), page.indexOf('data-role="retailer"'));
    expect(factory.indexOf(consequenceText("this_week", "Jonas"))).toBeLessThan(factory.indexOf("Sett inn KI-spiller for Jonas"));
    expect(page).toContain(consequenceText("next_week", "Sara"));
    // Secondary, full width below 1024 px.
    const button = page.match(/<button[^>]*data-takeover="factory"[^>]*>/)?.[0] ?? "";
    expect(button).toContain("w-full lg:w-auto");
  });

  it("shows nothing for a game not started or finished, or with no Student Seat", () => {
    expect(html(<Spillstyring data={insight("finished", SEATS)} />)).toBe("");
    expect(html(<Spillstyring data={insight("not_started", SEATS)} />)).toBe("");
    expect(html(<Spillstyring data={insight("running", [SEATS[1], SEATS[2]])} />)).toBe("");
  });

  it("names who came first from the view read again, never from the error", () => {
    const refused = new ApiRequestError(409, "takeover_exists", { acted_by: { kind: "staff", user_id: "u1" }, acted_at: "x" });
    expect(actedKind(refused)).toBe("staff");
    expect(actedKind(new ApiRequestError(409, "seat_not_student_held"))).toBeNull();
    expect(takenText("staff", "Sara")).toBe("Sara har allerede satt inn en KI-spiller.");
    expect(takenText("student", null)).toBe(copy.takenByUnknown);
    expect(takenText("system", "Sara")).toBe(copy.takenBySystem);
  });

  it("says any other refusal inline in its own words, else the fallback", () => {
    const said = (code: string) => actionErrorMessage(new ApiRequestError(409, code), copy.refusals, copy.failed);
    expect(said("seat_not_student_held")).toBe(copy.refusals.seat_not_student_held);
    expect(said("game_not_running")).toBe(copy.refusals.game_not_running);
    expect(said("order_exists")).toBe(copy.refusals.order_exists);
    expect(said("network_error")).toBe(copy.failed);
  });
});

describe("marks naming who put the AI player in", () => {
  it("reads «KI satt inn av Bård» on Spillinnsikt and the Oversikt; other marks keep their words", () => {
    expect(seatMarkText(SEATS[2])).toBe("KI satt inn av Bård");
    expect(seatMarkText({ ...SEATS[2], mark_by: null })).toBe(nb.insight.marks.takeover_staff);
    expect(markWords("takeover_inactivity", "Bård")).toBe(nb.insight.marks.takeover_inactivity);
    const game = {
      game_id: "g1",
      game_number: 1,
      status: "running" as const,
      week: 3,
      version: 1,
      chain_cost: null,
      wait_started_at: null,
      waiting_for: [],
      seats: [{ role: "factory" as const, holder: "ai" as const, name: null, mark: "takeover_staff" as const, mark_by: "Bård" }],
    };
    expect(seatTexts(game)).toEqual(["Fabrikk: KI-spiller (KI satt inn av Bård)"]);
    expect(seatMarks(game)).toEqual(["Fabrikk: KI satt inn av Bård"]);
  });
});

describe("the Varselbånd's Takeover", () => {
  it("names who came first from the Oversikt read again, by game and Role", () => {
    const items = [
      {
        game_id: "g2",
        game_number: 2,
        status: "waiting" as const,
        week: 3,
        version: 2,
        chain_cost: null,
        wait_started_at: null,
        waiting_for: [],
        seats: [
          { role: "wholesaler" as const, holder: "ai" as const, name: null, mark: "takeover_staff" as const, mark_by: "Sara" },
          { role: "factory" as const, holder: "student" as const, name: "Ida", mark: null, mark_by: null },
        ],
      },
    ];
    expect(markBy(items, "g2", "wholesaler")).toBe("Sara");
    expect(markBy(items, "g2", "factory")).toBeNull();
    expect(markBy(items, "g9", "wholesaler")).toBeNull();
  });

  it("adds the secondary «Sett inn KI-spiller for Noah» with its consequence under the band text", () => {
    const band = html(
      <OverviewBand
        alert={{ game_id: "g2", game_number: 2, role: "wholesaler", name: "Noah", user_id: "u", since: "2026-11-20T13:00:00Z" }}
        sessionId="s1"
        now={Date.parse("2026-11-21T12:00:00Z")}
      />,
    );
    expect(band).toContain(consequenceText("this_week", "Noah"));
    expect(band).toMatch(/<button[^>]*data-takeover="wholesaler"[^>]*>Sett inn KI-spiller for Noah<\/button>/);
    expect(band.indexOf("Send Melding")).toBeLessThan(band.indexOf("Sett inn KI-spiller for Noah"));
  });
});
