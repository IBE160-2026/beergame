import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

const copy = nb.sessions.dates;
const MONTHS = nb.admin.users.invitations.months;

/** The four dates in their order (FR-18): Startdato, Spillfrist, Debrieffrist, Testfrist. */
export const DATE_NAMES = ["start_at", "play_deadline", "debrief_deadline", "test_deadline"] as const;
export type DateName = (typeof DATE_NAMES)[number];

/** The four date fields as the Lecturer types them: Europe/Oslo wall time, «2026-11-24T10:00», or
 * "" for a date not set. */
export type DateInputs = Record<DateName, string>;

/** How many days after the Debrieffrist the Testfrist is prefilled (FR-18). */
export const TEST_AFTER_DEBRIEF_DAYS = 7;

const OSLO = new Intl.DateTimeFormat("en-GB", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "Europe/Oslo",
});

type Parts = { year: number; month: number; day: number; hour: number; minute: number };

/** The Europe/Oslo calendar parts of an instant. */
function osloParts(ms: number): Parts {
  const parts = OSLO.formatToParts(new Date(ms));
  const part = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  return { year: part("year"), month: part("month"), day: part("day"), hour: part("hour"), minute: part("minute") };
}

const pad = (n: number) => String(n).padStart(2, "0");

function toLocal(p: Parts): string {
  return `${p.year}-${pad(p.month)}-${pad(p.day)}T${pad(p.hour)}:${pad(p.minute)}`;
}

const LOCAL = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;

function parseLocal(local: string): Parts | null {
  const m = LOCAL.exec(local);
  if (!m) return null;
  const [year, month, day, hour, minute] = m.slice(1).map(Number);
  return { year, month, day, hour, minute };
}

/** The field value of an instant from the API: its Europe/Oslo wall time, or "" for none. */
export function toOsloInput(iso: string | null | undefined): string {
  return iso ? toLocal(osloParts(Date.parse(iso))) : "";
}

/**
 * The instant (ISO, UTC) of a Europe/Oslo wall time from a field, or null for an empty or
 * unreadable field. The offset is read from the time-zone data, so summer time is right; a wall
 * time skipped by the change to summer time moves forward by the gap.
 */
export function fromOsloInput(local: string): string | null {
  const p = parseLocal(local);
  if (!p) return null;
  const asUtc = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
  const offset = (ms: number) => {
    const o = osloParts(ms);
    return Date.UTC(o.year, o.month - 1, o.day, o.hour, o.minute) - ms;
  };
  let ms = asUtc - offset(asUtc);
  ms = asUtc - offset(ms);
  return new Date(ms).toISOString();
}

/** A field value `days` calendar days later, at the same wall time; "" when unreadable. */
export function addDays(local: string, days: number): string {
  const p = parseLocal(local);
  if (!p) return "";
  const d = new Date(Date.UTC(p.year, p.month - 1, p.day + days, p.hour, p.minute));
  return toLocal({
    year: d.getUTCFullYear(),
    month: d.getUTCMonth() + 1,
    day: d.getUTCDate(),
    hour: d.getUTCHours(),
    minute: d.getUTCMinutes(),
  });
}

/** «ti. 24. nov.» and «10:00»: an instant on the Datolinje, in Europe/Oslo. */
export function osloDayAndTime(iso: string): { day: string; time: string } {
  const p = osloParts(Date.parse(iso));
  const weekday = new Date(Date.UTC(p.year, p.month - 1, p.day)).getUTCDay();
  return {
    day: copy.day(copy.weekdays[weekday], p.day, MONTHS[p.month - 1]),
    time: `${pad(p.hour)}:${pad(p.minute)}`,
  };
}

/** The fields of a Class session as the API holds them. */
export function inputsOf(item: Record<DateName, string | null | undefined>): DateInputs {
  return {
    start_at: toOsloInput(item.start_at),
    play_deadline: toOsloInput(item.play_deadline),
    debrief_deadline: toOsloInput(item.debrief_deadline),
    test_deadline: toOsloInput(item.test_deadline),
  };
}

/** The body's `dates`: each field as an instant, or null. */
export function datesBody(inputs: DateInputs): Record<DateName, string | null> {
  return {
    start_at: fromOsloInput(inputs.start_at),
    play_deadline: fromOsloInput(inputs.play_deadline),
    debrief_deadline: fromOsloInput(inputs.debrief_deadline),
    test_deadline: fromOsloInput(inputs.test_deadline),
  };
}

/** The reason under each date the API refused (`invalid_dates`, `deadline_passed`). An order
 * error names the nearest earlier date that is filled in; a `before` error the nearest later. */
export function dateErrors(error: unknown, inputs: DateInputs): Partial<Record<DateName, string>> {
  if (!(error instanceof ApiRequestError)) return {};
  if (error.code !== "invalid_dates" && error.code !== "deadline_passed") return {};
  const result: Partial<Record<DateName, string>> = {};
  DATE_NAMES.forEach((name, index) => {
    const reason = error.fields[name];
    if (reason === "order") {
      const earlier = DATE_NAMES.slice(0, index)
        .reverse()
        .find((other) => inputs[other] !== "");
      result[name] = copy.errors.order(copy.names[earlier ?? DATE_NAMES[0]]);
    } else if (reason === "before") {
      const later = DATE_NAMES.slice(index + 1).find((other) => inputs[other] !== "");
      result[name] = copy.errors.before(copy.names[later ?? DATE_NAMES[DATE_NAMES.length - 1]]);
    } else if (reason === "past" || reason === "passed" || reason === "required") {
      result[name] = copy.errors[reason];
    }
  });
  return result;
}
