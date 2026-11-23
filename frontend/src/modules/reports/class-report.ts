import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import type { GameSettings } from "@/modules/sessions/api";
import { roleName } from "@/modules/sessions/sessions";

import type { ClassReport, ReportDistribution } from "./class-report-api";

/**
 * The Klasserapport's text and order (Story 14.1, UX-DR55, UX-DR73). Every number is the api's
 * (AD-10): these only pick the words, format with the shared number formatter and put Roles in the
 * order the spine asks: Fabrikk at the top in Role lists and charts, Detaljist to Fabrikk in
 * per-Role tables. The bars' shares only scale `aria-hidden` bars.
 */
const copy = nb.classReport;

type Role = GameSettings["roles"][number];

const gameName = (number: number | null) => nb.overview.game(number);

const whole = (value: string | number) => formatNumber(value, { decimals: 0 });
const tenth = (value: string | number) => formatNumber(value, { decimals: 1 });
const hundredth = (value: string | number) => formatNumber(value, { decimals: 2 });

export { hundredth, tenth, whole };

/** The line under the heading: none finished, some, or all (FR-64). */
export function statusLine(report: Pick<ClassReport, "games" | "finished">): string {
  if (report.games === 0) return copy.noGames;
  if (report.finished === 0) return copy.none;
  if (report.finished < report.games) return copy.partial(report.finished, report.games);
  return copy.all(report.games);
}

/** «Fra 38 av 41 ferdige spill. …» when the analysis of some, not all or none, finished games is
 * not stored yet. */
export function coveredLine(report: Pick<ClassReport, "finished" | "facts_games">): string | null {
  // With none analysed, the section's own «Ingen spill er analysert ennå.» says it once.
  return report.facts_games > 0 && report.facts_games < report.finished
    ? copy.covered(report.facts_games, report.finished)
    : null;
}

/** Role lists and charts: Fabrikk at the top (UX-DR73). The api sends the chain order. */
export function fabrikkFirst<T extends { role: Role }>(rows: readonly T[]): T[] {
  return [...rows].reverse();
}

/** «Median 1 954. Midterste halvdel 1 500–2 600.» in whole kroner. */
export function costSummary(spread: ReportDistribution, previous?: string | null): string {
  return copy.summary(
    whole(spread.median),
    whole(spread.lower_quartile),
    whole(spread.upper_quartile),
    previous != null ? whole(previous) : null,
  );
}

/** The highest value of several distributions: one axis for every Role (small multiples). */
export function sharedHighest(spreads: readonly (ReportDistribution | null | undefined)[]): number {
  let most = 0;
  for (const spread of spreads) {
    if (!spread) continue;
    for (const value of [...spread.values, spread.upper_quartile]) most = Math.max(most, Number(value));
  }
  return most;
}

export type CostRoleRow = { role: Role; name: string; median: string; middle: string; holding: string; backorder: string };

/** Kostnad per Rolle's table: Detaljist to Fabrikk, whole kroner. */
export function costRoleRows(cost: NonNullable<ClassReport["cost"]>): CostRoleRow[] {
  return cost.roles.map((row) => ({
    role: row.role,
    name: roleName(row.role),
    median: whole(row.distribution.median),
    middle: copy.middle(whole(row.distribution.lower_quartile), whole(row.distribution.upper_quartile)),
    holding: whole(row.holding_cost),
    backorder: whole(row.backorder_cost),
  }));
}

export type AmplificationRow = { role: Role; name: string; games: number; median: string | null; middle: string | null };

/** Forsterkning per Rolle's table: Detaljist to Fabrikk, two decimals. */
export function amplificationRows(rows: ClassReport["amplification"]): AmplificationRow[] {
  return rows.map((row) => ({
    role: row.role,
    name: roleName(row.role),
    games: row.games,
    median: row.distribution ? hundredth(row.distribution.median) : null,
    middle: row.distribution
      ? copy.middle(hundredth(row.distribution.lower_quartile), hundredth(row.distribution.upper_quartile))
      : null,
  }));
}

export type PatternBar = { pattern: string; name: string; count: string; games: string; share: number; reads: string };

/** «Mønstre», most common first as the api sends them, each bar a share of the most common. */
export function patternBars(patterns: ClassReport["patterns"]): PatternBar[] {
  const most = Math.max(0, ...patterns.map((p) => p.occurrences));
  return patterns.map((p) => ({
    pattern: p.pattern,
    name: p.name,
    count: whole(p.occurrences),
    games: whole(p.games),
    share: most > 0 ? p.occurrences / most : 0,
    reads: copy.patterns.reads(p.name, whole(p.occurrences), whole(p.games)),
  }));
}

/** «KI-spillere spilte 14 av 240 seter (5,8 %): 9 hele spillet, 5 en del av det.» */
export function aiSeatsLine(ai: ClassReport["ai"]): string {
  return copy.ai.seats(ai.ai_seats, ai.seats, tenth(ai.ai_percent ?? "0"), ai.whole_game);
}

/** FR-79: the share of LLM-held Seats the Play guard switched, or that none held an LLM player. */
export function guardLine(ai: ClassReport["ai"]): string {
  if (ai.llm_seats === 0 || ai.guard_percent == null) return copy.ai.noLlm;
  return copy.ai.guard(ai.guard_switched, ai.llm_seats, tenth(ai.guard_percent));
}

/** One switch by the cost limit or the Play guard, its mark in words from the one AD-15 mapping. */
export function switchLines(ai: ClassReport["ai"]): string[] {
  return ai.switches.map((one) =>
    copy.ai.switchLine(gameName(one.number ?? null), roleName(one.role), one.week, nb.insight.marks[one.mark]),
  );
}

export type LlmRow = { game: string; ordered: string; llm: string; share: string; fallback: string };

/** The Share of LLM Orders per game (FR-68), in game-number order as the api sends it. */
export function llmRows(ai: ClassReport["ai"]): LlmRow[] {
  return ai.games.map((game) => ({
    game: gameName(game.number ?? null),
    ordered: whole(game.ordered),
    llm: whole(game.llm),
    share: game.llm_percent == null ? copy.ai.noOrders : copy.ai.percent(tenth(game.llm_percent)),
    fallback: whole(game.fallback),
  }));
}

export type RatingBar = { rating: number; count: number; share: number; reads: string };

/** One AI mode's ratings 1–5 as bars, each a share of the most common value. */
export function ratingBars(mode: ClassReport["ratings"][number]): RatingBar[] {
  const most = Math.max(0, ...mode.values.map((v) => v.count));
  return mode.values.map((v) => ({
    rating: v.rating,
    count: v.count,
    share: most > 0 ? v.count / most : 0,
    reads: copy.ratings.reads(v.rating, v.count),
  }));
}

/** «LLM-spillere: 23 svar, median 4.» */
export function ratingLine(mode: ClassReport["ratings"][number]): string {
  return copy.ratings.line(modeName(mode.ai_mode), whole(mode.count), formatNumber(mode.median, { narrow: true }));
}

export function modeName(mode: string): string {
  return copy.ratings.modes[mode] ?? mode;
}
