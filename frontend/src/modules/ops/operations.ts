import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { percentText } from "@/modules/admin/ai-models";

import type { ErrorHour } from "./api";

const copy = nb.admin.operations;

/** The error sources in the order «Drift» stacks and lists them (Story 15.8). */
export const SOURCES = ["conservation_check", "job_failed", "api_error"] as const;
export type Source = (typeof SOURCES)[number];

/** Each source's fill in «Feil per time» and its key: theme tokens only (UX-DR1), drawn as SVG
 * fills, not text backgrounds. */
export const SOURCE_FILL: Record<Source, string> = {
  conservation_check: "var(--color-restordre)",
  job_failed: "var(--color-lager)",
  api_error: "var(--color-ink)",
};

export function sourceName(source: Source): string {
  return copy.errors.sources[source] ?? source;
}

/** The hour of an hour's start in Oslo time, «09». */
export function hourText(iso: string): string {
  const parts = new Intl.DateTimeFormat("nb-NO", {
    hour: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date(iso));
  return parts.find((part) => part.type === "hour")?.value ?? "";
}

/** Every counted error of one hour. */
export function hourTotal(hour: ErrorHour): number {
  return SOURCES.reduce((sum, source) => sum + hour[source], 0);
}

/** The top of the hour axis: the busiest hour, at least 1, so an empty day draws no bar. */
export function hourAxisTop(hours: readonly ErrorHour[]): number {
  return Math.max(1, ...hours.map(hourTotal));
}

/** A bar's share of its axis as a CSS percentage, never past 100 %. */
export function barPercent(value: number, top: number): string {
  if (top <= 0 || value <= 0) return "0%";
  return `${Math.min(100, (value / top) * 100)}%`;
}

/** «22,22 %» for «0.2222», «–» when there is nothing to share. */
export function shareText(share: string | null): string {
  return share === null ? nb.admin.aiCost.configs.none : percentText(share);
}

/** «1 250 ms». */
export function msText(value: number): string {
  return copy.times.ms(formatNumber(value));
}

/** The fallback kind's Norwegian name, else its mark. */
export function fallbackName(kind: string): string {
  return copy.fallback.kinds[kind] ?? kind;
}
