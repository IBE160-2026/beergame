import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { GameResult, MyGame } from "./api";
import result from "./fixtures/result-classic.json";
import { GameAction } from "./game-action";
import { GameEnd } from "./game-end";
import { cardState } from "./home";

/** Story 8.14 (FR-38, UX-DR62): a game the Play deadline playout took over. While AI players play
 * it out the Student is told so, with no Spillkort and no primary; once it has ended «Spillet er
 * ferdig» says it ended at the Spillfrist. The api decides (`played_out`); the page words it. */
function html(node: ReactNode): string {
  return renderToStaticMarkup(<QueryClientProvider client={new QueryClient()}>{node}</QueryClientProvider>);
}

const game = (over: Partial<MyGame> = {}): MyGame => ({
  id: "g",
  number: 17,
  role: "wholesaler",
  test_game: false,
  replay: false,
  class_session_id: "s",
  seats: [
    {
      role: "wholesaler",
      holder: "ai",
      name: null,
      mine: true,
      ordered: false,
      wait_started_at: null,
      mark: "playout",
      taken_over: false,
      ordering_for: null,
      guard_switched: false,
      reclaim_queued: false,
      can_insert: false,
      insert_agreed: false,
    },
  ],
  obligatory: false,
  can_pause: false,
  played_out: true,
  briefing_first: false,
  rules: {
    order_delay: 2,
    shipping_delay: 2,
    production_delay: 2,
    guided_weeks: 4,
    holding_cost: "0.50",
    backorder_cost: "1.00",
    capacity: [],
  },
  status: "running",
  week: 12,
  server_now: "2026-12-01T12:00:00Z",
  seat_state: null,
  turn: null,
  ...over,
});

describe("a game the Play deadline playout took over", () => {
  it("has no Spillkort and says AI players play it out, with a Lenke and no primary", () => {
    expect(cardState({ ...game(), seat_state: {} as MyGame["seat_state"] })).toBeNull();
    const action = html(<GameAction game={game()} primary />);
    expect(action).toContain(`data-playing-out="">${nb.homes.student.playingOut}</p>`);
    expect(action).not.toContain("bg-ink"); // never the primary button
    expect(action).toContain('href="/spill/g"');
  });

  it("says on «Spillet er ferdig» that it ended at the Spillfrist, and only then", () => {
    const ended = html(<GameEnd game={game({ status: "finished", week: null })} result={result as GameResult} />);
    expect(ended).toContain(nb.games.play.end.playedOut);
    const normal = html(
      <GameEnd game={game({ status: "finished", week: null, played_out: false })} result={result as GameResult} />,
    );
    expect(normal).not.toContain(nb.games.play.end.playedOut);
  });

  it("never blames anyone or tells how many Uker the AI players played", () => {
    for (const line of [nb.homes.student.playingOut, nb.games.play.end.playedOut]) {
      expect(line).not.toMatch(/\d|uke/i);
    }
  });
});
