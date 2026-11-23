import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import {
  addDays,
  calendarDateText,
  dateErrors,
  datesBody,
  datesEditable,
  fromOsloInput,
  frozenDates,
  inputsOf,
  osloDateText,
  osloDayAndTime,
  toOsloInput,
} from "./dates";

const copy = nb.sessions.dates;

describe("the date fields in Europe/Oslo (Story 5.2)", () => {
  it("reads an instant as Oslo wall time, in winter and in summer", () => {
    expect(toOsloInput("2026-11-24T09:00:00Z")).toBe("2026-11-24T10:00");
    expect(toOsloInput("2026-06-01T09:00:00Z")).toBe("2026-06-01T11:00");
    expect(toOsloInput(null)).toBe("");
  });

  it("sends Oslo wall time as UTC, both sides of a summer-time change", () => {
    expect(fromOsloInput("2026-11-24T10:00")).toBe("2026-11-24T09:00:00.000Z");
    expect(fromOsloInput("2026-06-01T11:00")).toBe("2026-06-01T09:00:00.000Z");
    expect(fromOsloInput("2026-03-29T01:30")).toBe("2026-03-29T00:30:00.000Z");
    expect(fromOsloInput("2026-03-29T03:30")).toBe("2026-03-29T01:30:00.000Z");
    // The skipped hour moves forward by the gap; the repeated hour in October reads as the later one (winter time).
    expect(fromOsloInput("2026-03-29T02:30")).toBe("2026-03-29T01:30:00.000Z");
    expect(fromOsloInput("2026-10-25T02:30")).toBe("2026-10-25T01:30:00.000Z");
    expect(fromOsloInput("")).toBeNull();
    expect(fromOsloInput("ikke en dato")).toBeNull();
  });

  it("adds whole calendar days at the same wall time, across a month", () => {
    expect(addDays("2026-12-11T23:59", 7)).toBe("2026-12-18T23:59");
    expect(addDays("2026-11-28T10:00", 7)).toBe("2026-12-05T10:00");
    expect(addDays("2026-10-20T23:00", 7)).toBe("2026-10-27T23:00");
    expect(addDays("", 7)).toBe("");
  });

  it("names a day as the Datolinje shows it", () => {
    expect(osloDayAndTime("2026-11-24T09:00:00Z")).toEqual({ day: "ti. 24. nov.", time: "10:00" });
  });

  it("words a frozen date as text, and saves dates only while one can still move (Story 5.11)", () => {
    expect(osloDateText("2026-11-24T09:00:00Z")).toBe("ti. 24. nov. kl.\u00a010:00");
    const all = ["start_at", "play_deadline", "debrief_deadline", "test_deadline"] as const;
    expect(datesEditable({ can_manage: true, passed_dates: ["start_at"] })).toBe(true);
    expect(datesEditable({ can_manage: true, passed_dates: [...all] })).toBe(false);
    expect(datesEditable({ can_manage: false, passed_dates: [] })).toBe(false);
    // Locked early, before the Startdato: it no longer moves either.
    expect(frozenDates({ passed_dates: [], locked_at: "2026-11-20T09:00:00Z" })).toEqual(["start_at"]);
    expect(frozenDates({ passed_dates: ["start_at"], locked_at: null })).toEqual(["start_at"]);
    expect(frozenDates({ passed_dates: [] })).toEqual([]);
  });

  it("builds the body from the fields, an empty field as null", () => {
    const inputs = inputsOf({
      start_at: "2026-11-24T09:00:00Z",
      play_deadline: null,
      debrief_deadline: undefined,
      test_deadline: "2026-12-18T22:59:00Z",
    });
    expect(inputs).toEqual({
      start_at: "2026-11-24T10:00",
      play_deadline: "",
      debrief_deadline: "",
      test_deadline: "2026-12-18T23:59",
    });
    expect(datesBody(inputs)).toEqual({
      start_at: "2026-11-24T09:00:00.000Z",
      play_deadline: null,
      debrief_deadline: null,
      test_deadline: "2026-12-18T22:59:00.000Z",
    });
  });

  it("words each refused date, naming the nearest earlier date filled in", () => {
    const inputs = { start_at: "2026-11-24T10:00", play_deadline: "", debrief_deadline: "2026-11-20T10:00", test_deadline: "" };
    const refused = new ApiRequestError(422, "invalid_dates", { debrief_deadline: "order", test_deadline: "past" });
    expect(dateErrors(refused, inputs)).toEqual({
      debrief_deadline: copy.errors.order(copy.names.start_at),
      test_deadline: copy.errors.past,
    });
    const passed = new ApiRequestError(409, "deadline_passed", { start_at: "passed" });
    expect(dateErrors(passed, inputs)).toEqual({ start_at: copy.errors.passed });
    expect(dateErrors(new ApiRequestError(409, "class_archived"), inputs)).toEqual({});
    const before = new ApiRequestError(422, "invalid_dates", { start_at: "before" });
    expect(dateErrors(before, inputs)).toEqual({ start_at: copy.errors.before(copy.names.debrief_deadline) });
  });
});

describe("calendarDateText (Story 13.9)", () => {
  it("writes a calendar day with the month word and the year, no time zone applied", () => {
    expect(calendarDateText("2027-06-18")).toBe("18. juni 2027");
    expect(calendarDateText("2027-01-01")).toBe("1. januar 2027");
    expect(calendarDateText("2028-02-29")).toBe("29. februar 2028");
  });
});
