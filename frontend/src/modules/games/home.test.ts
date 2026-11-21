import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import type { EnrolledSession } from "@/modules/sessions/api";

import week11 from "./fixtures/play-week-11.json";
import {
  cardState,
  deadlineText,
  gameTitle,
  holderText,
  labHourText,
  netSentence,
  nextAction,
  stepItems,
  toWeekText,
} from "./home";

const copy = nb.homes.student;
type Game = NonNullable<EnrolledSession["game"]>;
type Seat = Game["seats"][number];

const seat = (over: Partial<Seat>): Seat => ({
  role: "wholesaler",
  holder: "student",
  name: "Sara",
  mine: false,
  ordered: null,
  wait_started_at: null,
  mark: null,
  taken_over: false,
  ordering_for: null,
  guard_switched: false,
  reclaim_queued: false,
  ...over,
});

describe("Hjem's game card (Story 6.1)", () => {
  it("names the game and the Student's Role", () => {
    const game: Game = {
      id: "g",
      number: 17,
      role: "wholesaler",
      test_game: false,
      class_session_id: "s",
      seats: [],
      obligatory: false,
      can_pause: false,
      briefing_first: true,
      rules: {
        order_delay: 2,
        shipping_delay: 2,
        production_delay: 2,
        guided_weeks: 4,
        holding_cost: "0.50",
        backorder_cost: "1.00",
        capacity: [],
      },
      status: "ready",
      week: null,
      server_now: "2026-11-21T10:00:00Z",
      seat_state: null,
      turn: null,
    };
    expect(gameTitle(game)).toBe("Spill 17 · Du er Grossist");
    // Story 6.20: a Lecturer's test Game has no number and reads «Testspill» in plain text.
    expect(gameTitle({ ...game, number: null, test_game: true })).toBe("Testspill · Du er Grossist");
    expect(nb.games.play.roleGame("Grossist", null)).toBe("Grossist, Testspill");
  });

  it("says who holds each Seat in words, «KI-spiller» for every AI player", () => {
    expect(holderText(seat({}))).toBe("Sara");
    expect(holderText(seat({ mine: true }))).toBe("Sara (deg)");
    expect(holderText(seat({ holder: "ai", name: null }))).toBe("KI-spiller");
    expect(holderText(seat({ holder: "free", name: null }))).toBe(copy.free);
    expect(holderText(seat({ name: null }))).toBe(copy.removed);
    // Story 6.20: the Lecturer in their own test Game has no Student name.
    expect(holderText(seat({ name: null, mine: true }))).toBe(copy.youAlone);
  });
});

describe("Stegene's items (Story 6.1, AD-10)", () => {
  it("puts the api's states in words: «pågår», «ferdig» and what opens a later step", () => {
    const items = stepItems([
      { step: "class_game", state: "done" },
      { step: "debrief", state: "current" },
      { step: "replay", state: "locked" },
      { step: "test", state: "locked" },
    ]);
    expect(items.map((item) => item.note)).toEqual([
      "ferdig",
      "pågår",
      "Replay, åpnes når du har bestått Debrief-quizen.",
      "Individuell test, åpnes når du har fullført Replay.",
    ]);
    expect(items.map((item) => item.name)).toEqual(["Klassespill", "Debrief", "Replay", "Individuell test"]);
  });

  it("has a lock line for every step and no exclamation mark", () => {
    for (const line of Object.values(copy.locked)) expect(line).toMatch(/^[^!]+, åpnes [^!]+\.$/);
  });
});

describe("Hjem's dates", () => {
  it("names the next deadline by its kind and day in Europe/Oslo", () => {
    expect(deadlineText({ next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" } })).toBe("Spillfrist ti. 8. des.");
    expect(deadlineText({ next_deadline: null })).toBeNull();
  });

  it("gives a Lab hour its day, start time and place", () => {
    const lab = { id: "l", starts_at: "2026-11-26T13:15:00Z", ends_at: "2026-11-26T15:00:00Z", place: "Datalab A2" };
    expect(labHourText(lab)).toBe("to. 26. nov. 14:15, Datalab A2");
  });
});

describe("the game's next action (Story 6.5)", () => {
  it("leads through the briefing, then the start, then the open Week", () => {
    expect(nextAction({ briefing_first: true, status: "ready" })).toBe("rules");
    // A game another Student started still asks for the briefing first.
    expect(nextAction({ briefing_first: true, status: "running" })).toBe("rules");
    expect(nextAction({ briefing_first: false, status: "ready" })).toBe("start");
    expect(nextAction({ briefing_first: false, status: "not_ready" })).toBe("notReady");
    expect(nextAction({ briefing_first: false, status: "running" })).toBe("play");
    expect(nextAction({ briefing_first: false, status: "finished" })).toBeNull();
    expect(nextAction({ briefing_first: true, status: "finished" })).toBeNull();
  });

  it("names the open Week", () => {
    expect(toWeekText({ week: 11 })).toBe("Gå til Uke 11");
    expect(toWeekText({ week: null })).toBe("Gå til Uke 1");
  });
});

describe("Hjem's Spillkort state (Story 6.17, UX-DR28)", () => {
  const state = week11.seat_state as NonNullable<Game["seat_state"]>;
  const running = (own: Seat["ordered"], over: Partial<Game> = {}) => ({
    status: "running" as const,
    briefing_first: false,
    seats: [seat({ role: "factory", ordered: true }), seat({ mine: true, ordered: own })],
    seat_state: state,
    ...over,
  });

  it("waits for the Student until their own Seat has ordered, then waits for the others", () => {
    expect(cardState(running(false))).toBe("waitsForYou");
    expect(cardState(running(true))).toBe("ordered");
  });

  it("has no card unless the game runs with a seat_state and the briefing is behind the Student", () => {
    expect(cardState(running(false, { status: "ready" }))).toBeNull();
    expect(cardState(running(false, { status: "finished" }))).toBeNull();
    expect(cardState(running(false, { seat_state: null }))).toBeNull();
    expect(cardState(running(false, { briefing_first: true }))).toBeNull();
    expect(cardState(running(null))).toBeNull();
    expect(cardState({ ...running(false), seats: [seat({ ordered: false })] })).toBeNull();
  });

  it("has no card once an AI player took the Student's Seat over (Story 8.2)", () => {
    const taken = seat({ mine: true, holder: "ai", name: null, ordered: true, taken_over: true });
    expect(cardState({ ...running(true), seats: [taken] })).toBeNull();
  });

  it("says the hidden graph's value at nå in words, with a true minus", () => {
    expect(netSentence({ ...state, net_inventory: -13, week: 11 })).toBe("Netto lager −13 i Uke 11.");
    expect(netSentence({ ...state, net_inventory: 4, week: 2 })).toBe("Netto lager 4 i Uke 2.");
  });
});
