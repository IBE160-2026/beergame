import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import type { LabHour } from "./api";
import {
  checkLabHour,
  firstRefusedField,
  inputsOfLabHour,
  labHourBody,
  labHourLine,
  labHourRefusal,
  placesOf,
  withLabHour,
} from "./lab-hours";

const e = nb.sessions.labHours.errors;
const FILLED = { date: "2026-11-26", start: "14:15", end: "16:00", place: " Datalab A2 " };

function lab(id: string, starts_at: string, place = "Datalab A2"): LabHour {
  return { id, starts_at, ends_at: new Date(Date.parse(starts_at) + 7_200_000).toISOString(), place, ended: false };
}

describe("the Lab hour form (Story 5.6)", () => {
  it("sends Europe/Oslo wall time as UTC with the place trimmed", () => {
    expect(checkLabHour(FILLED)).toEqual({});
    expect(labHourBody(FILLED)).toEqual({
      starts_at: "2026-11-26T13:15:00.000Z",
      ends_at: "2026-11-26T15:00:00.000Z",
      place: "Datalab A2",
    });
  });

  it("reads a saved Lab hour back into the fields", () => {
    expect(inputsOfLabHour({ starts_at: "2026-06-04T12:15:00Z", ends_at: "2026-06-04T14:00:00Z", place: "Rom 1" })).toEqual(
      { date: "2026-06-04", start: "14:15", end: "16:00", place: "Rom 1" },
    );
  });

  it("names each empty field, and a half-typed one as not filled in, never as empty", () => {
    const empty = { date: "", start: "", end: "", place: "  " };
    expect(checkLabHour(empty)).toEqual({
      date: e.dateMissing,
      start: e.timeMissing,
      end: e.timeMissing,
      place: e.placeMissing,
    });
    expect(checkLabHour({ ...FILLED, date: "", start: "" }, { date: true, start: true })).toEqual({
      date: e.dateIncomplete,
      start: e.timeIncomplete,
    });
    expect(firstRefusedField(checkLabHour({ ...FILLED, place: "" }, { end: true }))).toBe("end");
  });

  it("refuses an end that is not after the start, and a place over 120 characters", () => {
    expect(checkLabHour({ ...FILLED, end: "14:15" })).toEqual({ end: e.endNotAfterStart });
    expect(checkLabHour({ ...FILLED, end: "09:00" })).toEqual({ end: e.endNotAfterStart });
    expect(checkLabHour({ ...FILLED, place: "x".repeat(121) })).toEqual({ place: e.placeTooLong });
  });

  it("words the api's refusals under their fields", () => {
    const refused = new ApiRequestError(422, "invalid_lab_hour", { ends_at: "past", place: "too_long" });
    expect(labHourRefusal(refused)).toEqual({ end: e.past, place: e.placeTooLong });
    expect(labHourRefusal(new ApiRequestError(422, "invalid_lab_hour", { ends_at: "too_long" }))).toEqual({ end: e.tooLong });
    expect(labHourRefusal(new ApiRequestError(409, "lab_hour_ended"))).toEqual({});
  });
});

describe("the Labtimer list and legend (Story 5.6)", () => {
  it("writes one line per Lab hour in Europe/Oslo", () => {
    expect(labHourLine(lab("a", "2026-11-26T13:15:00Z"))).toBe("to. 26. nov. 14:15–16:15, Datalab A2");
  });

  it("names each place once in the legend", () => {
    expect(placesOf([lab("a", "2026-11-26T13:15:00Z"), lab("b", "2026-11-27T13:15:00Z")])).toBe("Datalab A2");
    const three = ["Datalab A2", "Rom 101", "Datalab A2", "Aula"].map((place, i) => lab(String(i), "2026-11-26T13:15:00Z", place));
    expect(placesOf(three)).toBe("Datalab A2, Rom 101 og Aula");
  });

  it("keeps the cached list in order as Lab hours are added, changed and removed", () => {
    const first = lab("a", "2026-11-26T13:15:00Z");
    const second = lab("b", "2026-11-28T13:15:00Z");
    const list = withLabHour([second], first);
    expect(list.map((item) => item.id)).toEqual(["a", "b"]);
    expect(withLabHour(list, { ...first, starts_at: "2026-11-29T13:15:00Z" }).map((item) => item.id)).toEqual(["b", "a"]);
    expect(withLabHour(list, null, "a").map((item) => item.id)).toEqual(["b"]);
  });
});
