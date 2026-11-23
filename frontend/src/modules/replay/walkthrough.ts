import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { Walkthrough, WalkthroughRun } from "./api";

const copy = nb.replay.walkthrough;

/** What the Replay-gjennomgang shows (Story 10.7), from the api's answer or its error code alone
 * (AD-10): the access-denied page for anyone but the Replay's Student, Story 10.6's closed message
 * for a Replay closed at the Testfrist, a line for one not finished, «Gjennomgangen lages.» while
 * its line is worded, else the walkthrough. */
export type WalkthroughView = "denied" | "closed" | "notFinished" | "pending" | "ready" | "waiting";

export function walkthroughView(data: Walkthrough | undefined, code: string | null): WalkthroughView {
  if (code === "forbidden") return "denied";
  if (code === "replay_closed") return "closed";
  if (code === "replay_not_finished") return "notFinished";
  if (!data) return "waiting";
  return data.state === "pending" ? "pending" : "ready";
}

/** One Uke of one run, formatted as the table shows it. */
export type RunCells = { net: number; order: string; cost: string };

/** One table row: an Uke and each run's cells; a run that has no such Uke (one is shorter) has
 * none. */
export type WalkthroughRow = { week: number; replay: RunCells | null; klass: RunCells | null };

/** A run's Uker as the walkthrough and the Student report (Story 13.10) both read them. */
type RunWeeks = { weeks: readonly Pick<WalkthroughRun["weeks"][number], "week" | "net_inventory" | "order" | "total_cost">[] };
/** The two runs set side by side: the Replay's and, unless left out, the Class game's. */
export type Runs = { replay?: RunWeeks | null; class_game?: RunWeeks | null };

function cells(run: RunWeeks | null | undefined): Map<number, RunCells> {
  return new Map(
    (run?.weeks ?? []).map((w) => [
      w.week,
      { net: w.net_inventory, order: formatNumber(w.order), cost: formatNumber(w.total_cost, { kroner: true }) },
    ]),
  );
}

/** «Vis som tabell»: every Uke of either run, in order, with the Replay's and the Class game's
 * Netto lager, Din ordre and Kostnad så langt side by side (the chart's columns and more). */
export function walkthroughRows<T extends Runs>(data: T): WalkthroughRow[] {
  const replay = cells(data.replay);
  const klass = cells(data.class_game);
  const weeks = [...new Set([...replay.keys(), ...klass.keys()])].sort((a, b) => a - b);
  return weeks.map((week) => ({ week, replay: replay.get(week) ?? null, klass: klass.get(week) ?? null }));
}

/** «Ikke like for like.» and its reasons in words (FR-50, UX-DR70): AI neighbours, other demand,
 * and each run's number of Uker. Never which run was better. */
export function unlikeReasons<T extends Runs>(data: T): string[] {
  const replayWeeks = data.replay?.weeks.length ?? 0;
  const classWeeks = data.class_game?.weeks.length ?? 0;
  return [copy.unlikeNeighbours, copy.unlikeDemand, copy.unlikeWeeks(replayWeeks, classWeeks)];
}

/** Totalkostnad of each run by the shared formatter («220,50 kr»); the Class game's null when it is
 * not shown (`mostly_ai`). */
export function walkthroughTotals(data: Walkthrough): { replay: string | null; klass: string | null } {
  return {
    replay: data.replay ? formatNumber(data.replay.total_cost, { kroner: true }) : null,
    klass: data.class_game ? formatNumber(data.class_game.total_cost, { kroner: true }) : null,
  };
}
