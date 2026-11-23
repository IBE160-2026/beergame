import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { ComparedMeasure, ComparedSession, CrossClass, DiffKey, FilterDimension, FilterOption } from "./cross-class-api";

/**
 * Tverrklasse-statistikk's words and order (Story 14.3, FR-65, UX-DR55). Every figure is a stored
 * aggregate's (AD-10, AD-14): these only name the Class sessions and measures, format the values
 * with the shared number formatter and scale the `aria-hidden` bars. A withheld figure (a group
 * under 10 Students) and one not measured are said in words, never drawn. Story 14.4: the filter
 * options and the difference labels are the api's; these only name them.
 */
const copy = nb.crossClass;

export function sessionName(session: Pick<ComparedSession, "class_name" | "session_number">): string {
  return copy.session(session.class_name, session.session_number);
}

/** Fewer than two Class sessions: nothing to compare with. */
export function nothingToCompare(data: CrossClass): boolean {
  return data.sessions.length < 2;
}

/** The Class sessions with a stored aggregate (`ready`), those the api compares under the filters
 * (`compared`), and those without an aggregate (listed only). */
export function splitSessions(data: CrossClass): {
  ready: ComparedSession[];
  compared: ComparedSession[];
  waiting: ComparedSession[];
} {
  return {
    ready: data.sessions.filter((session) => session.written_at != null),
    compared: data.sessions.filter((session) => session.compared),
    waiting: data.sessions.filter((session) => session.written_at == null),
  };
}

/** A filter option's name: the api's label is data (a code, a model's name, prompt versions). */
export function optionName(dimension: FilterDimension, option: Pick<FilterOption, "label" | "ordinal">): string {
  if (dimension === "game_settings") return option.label === "classic" ? copy.classic : copy.otherSettings(option.ordinal);
  if (option.label == null) return copy.none;
  if (dimension === "ai_mode") return copy.aiModes[option.label] ?? option.label;
  return option.label;
}

/** «Ulikt oppsett: KI-modus, modell», or null for a Class session that differs in nothing. */
export function differsText(differs: readonly DiffKey[]): string | null {
  if (differs.length === 0) return null;
  return copy.differs(differs.map((key) => copy.differKeys[key] ?? key).join(", "));
}

/** A score measure's comparability line; null for a measure that is no score or not judged. */
export function comparableText(measure: Pick<ComparedMeasure, "comparable">): string | null {
  if (measure.comparable == null) return null;
  return measure.comparable ? copy.scoresComparable : copy.scoresNotComparable;
}

export function measureName(key: string): string {
  return copy.measures[key] ?? key;
}

/** A value in its unit: kroner whole, Forsterkning to two decimals, percent and points to one. */
export function formatValue(unit: ComparedMeasure["unit"], value: string): string {
  switch (unit) {
    case "kroner":
      return copy.kroner(formatNumber(value, { decimals: 0 }));
    case "ratio":
      return copy.ratio(formatNumber(value, { decimals: 2 }));
    case "percent":
      return copy.percent(formatNumber(value, { decimals: 1 }));
    case "points":
      return copy.points(formatNumber(value, { decimals: 1 }));
  }
}

export type CompareRow = {
  key: string;
  session: string;
  text: string;
  /** The bar's length, 0 to 1 of the measure's highest value; null for a figure not drawn. */
  share: number | null;
  /** «Ulikt oppsett: …», or null when the Class session differs in nothing. */
  differs: string | null;
  reads: string;
};

/** One measure's rows in the order of the Class sessions. */
export function compareRows(measure: ComparedMeasure, sessions: readonly ComparedSession[]): CompareRow[] {
  const byId = new Map(sessions.map((session) => [session.class_session_id, session]));
  const numbers = measure.values.flatMap((value) => (value.value != null ? [Number(value.value)] : []));
  const highest = Math.max(0, ...numbers);
  return measure.values.map((value) => {
    const found = byId.get(value.class_session_id);
    const session = found ? sessionName(found) : value.class_session_id;
    const text = value.value != null ? formatValue(measure.unit, value.value) : value.withheld ? copy.withheld : copy.notMeasured;
    const share = value.value != null ? (highest > 0 ? Math.max(0, Number(value.value)) / highest : 0) : null;
    const differs = found ? differsText(found.differs) : null;
    const reads = differs ? copy.readsWithDiffers(session, text, differs) : copy.reads(session, text);
    return {
      key: value.class_session_id,
      session,
      text,
      share,
      differs,
      reads,
    };
  });
}
