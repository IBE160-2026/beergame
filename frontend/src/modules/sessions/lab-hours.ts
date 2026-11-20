import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import type { LabHour, LabHourIn } from "./api";
import { fromOsloInput, osloDayAndTime, toOsloInput } from "./dates";

const copy = nb.sessions.labHours;

/** The Lab hour form as typed (Story 5.6): a date «2026-11-26», start and end «14:15» in
 * Europe/Oslo on that date, and the place. */
export type LabHourInputs = { date: string; start: string; end: string; place: string };
export type LabHourField = keyof LabHourInputs;
export type LabHourErrors = Partial<Record<LabHourField, string>>;
/** The fields the browser holds half-typed (`validity.badInput`): their value reads as "", but they
 * are not empty (GitHub issue 100). */
export type HalfTyped = Partial<Record<Exclude<LabHourField, "place">, boolean>>;

export const LAB_HOUR_FIELDS: readonly LabHourField[] = ["date", "start", "end", "place"];
export const EMPTY_LAB_HOUR: LabHourInputs = { date: "", start: "", end: "", place: "" };
/** The longest place, as the api holds it. */
export const PLACE_MAX = 120;

/** The form's values of a saved Lab hour, in Europe/Oslo. */
export function inputsOfLabHour(lab: Pick<LabHour, "starts_at" | "ends_at" | "place">): LabHourInputs {
  const [date, start] = toOsloInput(lab.starts_at).split("T");
  const end = toOsloInput(lab.ends_at).split("T")[1];
  return { date, start, end, place: lab.place };
}

/** The instant of a time on the form's date, or null while either is not filled in. */
function instant(date: string, time: string): string | null {
  return date && time ? fromOsloInput(`${date}T${time}`) : null;
}

/**
 * What the form says before anything is sent: a field that is empty or half-typed gets its own
 * reason, never read as empty in silence, and an end not after the start is refused. The api
 * judges the rest (a Lab hour that has ended, one over 12 hours).
 */
export function checkLabHour(inputs: LabHourInputs, halfTyped: HalfTyped = {}): LabHourErrors {
  const e = copy.errors;
  const errors: LabHourErrors = {};
  if (halfTyped.date) errors.date = e.dateIncomplete;
  else if (!inputs.date) errors.date = e.dateMissing;
  for (const field of ["start", "end"] as const) {
    if (halfTyped[field]) errors[field] = e.timeIncomplete;
    else if (!inputs[field]) errors[field] = e.timeMissing;
  }
  const place = inputs.place.trim();
  if (!place) errors.place = e.placeMissing;
  else if (place.length > PLACE_MAX) errors.place = e.placeTooLong;
  if (!errors.start && !errors.end && inputs.end <= inputs.start) errors.end = e.endNotAfterStart;
  return errors;
}

/** The body the api takes; only called once `checkLabHour` found nothing. */
export function labHourBody(inputs: LabHourInputs): LabHourIn {
  return {
    starts_at: instant(inputs.date, inputs.start) ?? "",
    ends_at: instant(inputs.date, inputs.end) ?? "",
    place: inputs.place.trim(),
  };
}

/** The reason under each field the api refused (`invalid_lab_hour`). */
export function labHourRefusal(error: unknown): LabHourErrors {
  if (!(error instanceof ApiRequestError) || error.code !== "invalid_lab_hour") return {};
  const e = copy.errors;
  const errors: LabHourErrors = {};
  const end = error.fields.ends_at;
  if (end === "not_after_start") errors.end = e.endNotAfterStart;
  else if (end === "too_long") errors.end = e.tooLong;
  else if (end === "past") errors.end = e.past;
  const place = error.fields.place;
  if (place === "required") errors.place = e.placeMissing;
  else if (place === "too_long") errors.place = e.placeTooLong;
  return errors;
}

/** The first field in the form's order that has a reason. */
export function firstRefusedField(errors: LabHourErrors): LabHourField | undefined {
  return LAB_HOUR_FIELDS.find((field) => errors[field]);
}

/** «to. 26. nov. 14:15–16:00, Datalab A2». */
export function labHourLine(lab: Pick<LabHour, "starts_at" | "ends_at" | "place">): string {
  const start = osloDayAndTime(lab.starts_at);
  return copy.item(start.day, start.time, osloDayAndTime(lab.ends_at).time, lab.place);
}

/** The places of the legend, each once in the order first met: «Datalab A2 og Rom 101». */
export function placesOf(labs: readonly Pick<LabHour, "place">[]): string {
  return nb.sessions.chain.list([...new Set(labs.map((lab) => lab.place))]);
}

/** The cached list after a Lab hour was added, changed (`lab` replaces its id) or removed. */
export function withLabHour(list: readonly LabHour[], lab: LabHour | null, removedId?: string): LabHour[] {
  const rest = list.filter((item) => item.id !== (lab?.id ?? removedId));
  const next = lab ? [...rest, lab] : rest;
  return next.sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at) || a.id.localeCompare(b.id));
}
