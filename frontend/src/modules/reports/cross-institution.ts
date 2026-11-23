import { nb } from "@/copy/nb";

import { type CompareRow, differsText, formatValue } from "./cross-class";
import type { ComparedInstitution, InstitutionMeasure } from "./cross-institution-api";

/**
 * «Tverrinstitusjonell statistikk»'s rows (Story 14.7, cut list, FR-65). Every figure is the api's
 * (AD-10, AD-14): these only name the Institutions, format the values with the shared number
 * formatter (through Tverrklasse-statistikk's `formatValue`) and scale the `aria-hidden` bars. A
 * withheld figure and one not measured are said in words, never drawn.
 */
const copy = nb.crossInstitution;
const words = nb.crossClass;

export type InstitutionRow = CompareRow & {
  /** The figure alone (or the words for one not shown), for the table's «Verdi». */
  figure: string;
  /** How many Class sessions the figure rests on (0 when none is shown). */
  sessions: number;
};

/** One measure's rows in the order of the Institutions, as Tverrklasse-statistikk's bars take them:
 * the Institution's name, its figure with how many Class sessions it rests on, and what differs. */
export function institutionRows(
  measure: InstitutionMeasure,
  institutions: readonly ComparedInstitution[],
): InstitutionRow[] {
  const byId = new Map(institutions.map((institution) => [institution.institution_id, institution]));
  const numbers = measure.values.flatMap((value) => (value.value != null ? [Number(value.value)] : []));
  const highest = Math.max(0, ...numbers);
  return measure.values.map((value) => {
    const found = byId.get(value.institution_id);
    const name = found?.name ?? value.institution_id;
    const figure =
      value.value != null
        ? formatValue(measure.unit, value.value)
        : found?.withheld
          ? copy.withheld
          : value.withheld
            ? words.withheld
            : words.notMeasured;
    const text = value.value != null ? copy.value(figure, value.sessions) : figure;
    const share = value.value != null ? (highest > 0 ? Math.max(0, Number(value.value)) / highest : 0) : null;
    const differs = found ? differsText(found.differs) : null;
    const reads = differs ? words.readsWithDiffers(name, text, differs) : words.reads(name, text);
    return { key: value.institution_id, session: name, text, figure, sessions: value.sessions, share, differs, reads };
  });
}
