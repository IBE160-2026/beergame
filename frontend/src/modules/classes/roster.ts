import { nb } from "@/copy/nb";

import type { RosterUpload } from "./api";

const copy = nb.classes.roster;

type Column = RosterUpload["columns"][number];

/** A column as the «E-postkolonne» selector names it: «Kolonne C, E-post». */
export function columnLabel(column: Column): string {
  return copy.column(column.letter, column.header);
}

/**
 * The line under «E-postkolonne» (UX-DR47). The preselected column carries its reason, «Kolonne C,
 * E-post. Valgt fordi alle rader unntatt fire ser ut som adresser.»; a column the Lecturer chose
 * carries the api's count for it; with no column chosen, the page says that no column looks like
 * addresses. Every count comes from the api's evaluation of the staged rows.
 */
export function columnReason(upload: RosterUpload): string {
  const chosen = upload.chosen_column;
  if (chosen === null || chosen === undefined) return copy.noEmailColumn;
  const column = upload.columns[chosen];
  const label = column ? columnLabel(column) : "";
  const reason =
    chosen === upload.suggested_column && upload.chosen_count > 0
      ? copy.suggested(upload.valid_count, upload.row_count)
      : copy.chosen(upload.chosen_count, upload.valid_count, upload.row_count);
  return label ? `${label}. ${reason}` : reason;
}

/** The value column's name in the invalid-row list: the chosen column's header, or «Kolonne C»
 * when it has none; pasted addresses are «Innlimt verdi» (Issue #86). */
export function invalidValueLabel(upload: RosterUpload): string {
  if (upload.source === "paste") return copy.invalidPasted;
  const column = upload.chosen_column === null || upload.chosen_column === undefined ? undefined : upload.columns[upload.chosen_column];
  return column ? copy.invalidValue(column.header, column.letter) : copy.invalidValue("", "");
}

/** Whether the chosen column holds no address at all: its reason line is then shown as an error,
 * not a hint (Issue #85). With no column chosen the line is guidance, not an error. */
export function columnHasNoAddress(upload: RosterUpload): boolean {
  return upload.chosen_column !== null && upload.chosen_column !== undefined && upload.chosen_count === 0;
}

type InvalidRow = RosterUpload["invalid_rows"][number];

/** Why a row gets no Invitation, in text (Story 4.3, NFR-6): «Domene mangler», «Dublett av rad 2». */
export function invalidReason(row: InvalidRow): string {
  if (row.reason === "duplicate") return copy.duplicate(row.first_row ?? 0);
  if (row.reason === "on_roster") return copy.onRoster;
  return copy.reasons[row.reason];
}

/** The range of whole days a sending may be valid for: the api's own (`classes.schemas`). */
export const VALID_DAYS = { default: 14, min: 1, max: 60 } as const;

/** The validity the Lecturer typed as whole days, or null when it is not a whole number in the
 * range: the field then says so and nothing is sent. */
export function parseValidDays(value: string): number | null {
  const trimmed = value.trim();
  if (!/^\d+$/.test(trimmed)) return null;
  const days = Number(trimmed);
  return days >= VALID_DAYS.min && days <= VALID_DAYS.max ? days : null;
}

/** A day as the result line names it, «3. desember»; the year only when it is not this year's
 * (`today` is an ISO date, from the browser's clock). */
export function dayLabel(isoDate: string, today: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  const base = `${day}. ${copy.months[month - 1]}`;
  return today.slice(0, 4) === String(year) ? base : `${base} ${year}`;
}
