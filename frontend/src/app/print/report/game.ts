import type { StockBacklogMost } from "@/components/charts/stock-backlog";
import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";
import type { ChartGame } from "@/modules/games/chain-charts";
import { roleName } from "@/modules/sessions/sessions";

import { reportCopy } from "./copy";

/**
 * The game section's model (Story 13.8, FR-58, FR-34, AD-15): which Uker each chart block holds,
 * the one scale every block shares, and who played each Role in words. Every number is the
 * snapshot's (AD-10); this file only groups and words them.
 */

export type GameData = components["schemas"]["ReportGameOut"];
type GameRole = GameData["roles"][number];

const copy = reportCopy.game.holders;

/** The most Uke columns one chart block holds on A4 at the report's fixed widths (136 px of row
 * labels, 28 px per Uke, 13 px text: 640 px of the 672 px between the margins). */
export const BLOCK_WEEKS = 18;

/** The Uker 1 … n in as few even blocks as fit: 36 → 1–18, 19–36; 20 → 1–10, 11–20. */
export function weekBlocks(weeks: readonly number[], most = BLOCK_WEEKS): { from: number; to: number }[] {
  if (weeks.length === 0) return [];
  const sorted = [...weeks].sort((a, b) => a - b);
  const count = Math.ceil(sorted.length / most);
  const size = Math.ceil(sorted.length / count);
  const blocks: { from: number; to: number }[] = [];
  for (let i = 0; i < sorted.length; i += size) {
    const part = sorted.slice(i, i + size);
    blocks.push({ from: part[0]!, to: part[part.length - 1]! });
  }
  return blocks;
}

/** The chain of `game` cut to the Uker `from` … `to`, for one chart block. */
export function inWeeks(game: ChartGame, from: number, to: number): ChartGame {
  const within = (week: number) => week >= from && week <= to;
  return {
    roles: game.roles.map((role) => ({ ...role, weeks: role.weeks.filter((week) => within(week.week)) })),
    demand: game.demand.filter((week) => within(week.week)),
  };
}

/** The game's largest Order (the customers' demand included): the Ordrestolper's one scale. */
export function largestOrder(game: ChartGame): number {
  return Math.max(
    0,
    ...game.roles.flatMap((role) => role.weeks.map((week) => week.order ?? 0)),
    ...game.demand.map((week) => week.demand),
  );
}

/** The game's largest stock and backlog: «Lager og restordre»'s one scale. */
export function stockMost(game: ChartGame): StockBacklogMost {
  const weeks = game.roles.flatMap((role) => role.weeks);
  return {
    stock: Math.max(0, ...weeks.map((week) => week.inventory)),
    backlog: Math.max(0, ...weeks.map((week) => week.backlog)),
  };
}

const HOLDER: Record<GameRole["weeks"][number]["holder"], string> = {
  student: copy.student,
  ai: copy.ai,
  free: copy.free,
};

/** Who held the Seat, by runs of Uker: «Student, uke 1–4», «KI-spiller, uke 5–20». Never who
 * the Student was: other Students are told apart by Role only (FR-58). */
export function holderRuns(role: Pick<GameRole, "weeks">): string[] {
  const runs: { who: string; from: number; to: number }[] = [];
  for (const week of role.weeks) {
    const who = HOLDER[week.holder];
    const last = runs[runs.length - 1];
    if (last && last.who === who && last.to === week.week - 1) last.to = week.week;
    else runs.push({ who, from: week.week, to: week.week });
  }
  return runs.map((run) => copy.range(run.who, run.from, run.to));
}

/** Each marked Uke in words, from the one AD-15 mapping's marks: «Uke 21: KI tok over etter
 * ventetiden.» */
export function markLines(role: Pick<GameRole, "weeks">): string[] {
  return role.weeks.flatMap((week) => week.marks.map((mark) => copy.mark(week.week, nb.insight.marks[mark])));
}

/** A Role's name in the report's chain, the Student's own with «(deg)». */
export function chainRoleName(role: GameRole["role"], own: GameRole["role"]): string {
  return role === own ? `${roleName(role)} ${nb.insight.charts.orders.own}` : roleName(role);
}
