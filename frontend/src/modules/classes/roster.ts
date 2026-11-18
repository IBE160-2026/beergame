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
