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
    chosen === upload.suggested_column
      ? copy.suggested(upload.chosen_count, upload.row_count)
      : copy.chosen(upload.chosen_count, upload.row_count);
  return label ? `${label}. ${reason}` : reason;
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
  return copy.reasons[row.reason];
}
