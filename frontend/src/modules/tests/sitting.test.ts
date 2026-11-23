import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import {
  DEFAULT_MINUTES,
  minutesLeft,
  minutesProblem,
  refusedMinutes,
  sittingBody,
  sittingChanged,
  sittingDraftOf,
  sittingEnd,
} from "./sitting";

const copy = nb.tests;
const stored = (minutes: number | null) => ({
  test_sitting: { minutes, min_minutes: 15, max_minutes: 240, can_change: true },
});

describe("the time left in a timed sitting (Story 11.12)", () => {
  const ends = "2026-12-01T10:00:00Z";
  const at = (iso: string) => Date.parse(iso);

  it("counts whole minutes from the server's clock, rounded up, never below 0", () => {
    expect(minutesLeft(ends, at("2026-12-01T09:22:00Z"))).toBe(38);
    expect(minutesLeft(ends, at("2026-12-01T09:59:01Z"))).toBe(1);
    expect(minutesLeft(ends, at("2026-12-01T10:00:00Z"))).toBe(0);
    expect(minutesLeft(ends, at("2026-12-01T10:05:00Z"))).toBe(0);
    expect(copy.individual.timed.timeLeft(38)).toBe("Tid igjen 38 min");
  });

  it("ends the sitting only when it ends before the Testfrist", () => {
    expect(sittingEnd({ sitting_ends_at: ends, test_deadline: "2026-12-02T00:00:00Z" })).toBe(ends);
    expect(sittingEnd({ sitting_ends_at: ends, test_deadline: null })).toBe(ends);
    expect(sittingEnd({ sitting_ends_at: ends, test_deadline: ends })).toBeNull();
    expect(sittingEnd({ sitting_ends_at: null, test_deadline: ends })).toBeNull();
  });
});

describe("the Klasseøkt's time limit draft (Story 11.12)", () => {
  it("starts from what is stored, or off with the default minutes", () => {
    expect(sittingDraftOf(stored(60))).toEqual({ on: true, minutes: "60" });
    expect(sittingDraftOf(stored(null))).toEqual({ on: false, minutes: String(DEFAULT_MINUTES) });
  });

  it("asks for whole minutes in the range, with the range in the reason", () => {
    const item = stored(null);
    const reason = "Skriv et helt antall minutter fra 15 til 240.";
    expect(minutesProblem({ on: true, minutes: "90" }, item)).toBeUndefined();
    expect(minutesProblem({ on: true, minutes: " 15 " }, item)).toBeUndefined();
    expect(minutesProblem({ on: true, minutes: "240" }, item)).toBeUndefined();
    for (const wrong of ["14", "241", "", "90.5", "-5", "abc", "1e2"]) {
      expect(minutesProblem({ on: true, minutes: wrong }, item)).toBe(reason);
    }
    expect(minutesProblem({ on: false, minutes: "abc" }, item)).toBeUndefined();
  });

  it("sends a change only, as minutes or null", () => {
    expect(sittingChanged({ on: true, minutes: "60" }, stored(60))).toBe(false);
    expect(sittingChanged({ on: true, minutes: "75" }, stored(60))).toBe(true);
    expect(sittingChanged({ on: false, minutes: "60" }, stored(60))).toBe(true);
    expect(sittingChanged({ on: false, minutes: "90" }, stored(null))).toBe(false);
    expect(sittingChanged({ on: true, minutes: "90" }, stored(null))).toBe(true);
    expect(sittingBody({ on: true, minutes: " 75 " })).toEqual({ minutes: 75 });
    expect(sittingBody({ on: false, minutes: "75" })).toEqual({ minutes: null });
  });

  it("shows the api's refusal of the minutes at the field", () => {
    const refused = new ApiRequestError(422, "invalid_session_values", { test_sitting_minutes: "out_of_range" });
    expect(refusedMinutes(refused, stored(null))).toBe("Skriv et helt antall minutter fra 15 til 240.");
    const other = new ApiRequestError(422, "invalid_session_values", { inactivity_limit_hours: "below_minimum" });
    expect(refusedMinutes(other, stored(null))).toBeUndefined();
    expect(refusedMinutes(new Error("x"), stored(null))).toBeUndefined();
  });
});
