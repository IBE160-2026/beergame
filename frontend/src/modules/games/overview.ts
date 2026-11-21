import { nb } from "@/copy/nb";
import { formatNumber, KRONER } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import { GAME_COLUMN, type TableColumn, type TableRow } from "@/components/charts/matrix-table";
import type { TableSort } from "@/components/charts/matrix-table-sort";
import type { WallGroup, WallRow } from "@/components/charts/matrix-wall";

import type { ClassOverview, GameWeeks, OverviewGame } from "./api";
import { waitDuration } from "./seat-status";

const copy = nb.overview;
const wall = nb.wall;

export type GroupName = "waiting" | "running" | "notStarted" | "finished";
export type OverviewGroup = { name: GroupName; title: string; games: OverviewGame[] };

/** «41 ferdig · 15 pågår · 4 venter», with «· 3 ikke startet» only when some have not started
 * (FR-39). The counts are the api's; nothing here counts Weeks or hints at a game's length. */
export function headline(counts: ClassOverview["counts"]): string {
  const parts = [copy.counts.finished(counts.finished), copy.counts.running(counts.running), copy.counts.waiting(counts.waiting)];
  if (counts.not_started > 0) parts.push(copy.counts.notStarted(counts.not_started));
  return parts.join(" · ");
}

const time = (iso: string | null | undefined) => (iso ? Date.parse(iso) : Number.POSITIVE_INFINITY);
const cost = (game: OverviewGame) => (game.chain_cost == null ? Number.POSITIVE_INFINITY : Number(game.chain_cost));
const number = (game: OverviewGame) => game.game_number ?? Number.POSITIVE_INFINITY;

/** The rows the api sent, grouped by status in the order Venter, Pågår, Ikke startet, Ferdig, each
 * header with its count (UX-DR40). Venter puts the longest wait first, Ferdig the lowest chain
 * cost; the others keep the game number. Empty groups are left out. Only groups and sorts what it
 * received (AD-10). */
export function groupsOf(games: readonly OverviewGame[]): OverviewGroup[] {
  const byNumber = (a: OverviewGame, b: OverviewGame) => number(a) - number(b);
  const pick = (status: OverviewGame["status"]) => games.filter((game) => game.status === status);
  const groups: OverviewGroup[] = [
    {
      name: "waiting",
      title: copy.groups.waiting,
      games: pick("waiting").sort((a, b) => time(a.wait_started_at) - time(b.wait_started_at) || byNumber(a, b)),
    },
    { name: "running", title: copy.groups.running, games: pick("running").sort(byNumber) },
    { name: "notStarted", title: copy.groups.notStarted, games: pick("not_started").sort(byNumber) },
    {
      name: "finished",
      title: copy.groups.finished,
      games: pick("finished").sort((a, b) => cost(a) - cost(b) || byNumber(a, b)),
    },
  ];
  return groups.filter((group) => group.games.length > 0);
}

/** «Venter på Noah (Grossist), 23 t» for each Seat the game waits for, counted at `now` (ms on
 * the server's clock). A Student no longer in the Class is named by Role. */
export function waitLines(game: OverviewGame, now: number): string[] {
  return game.waiting_for.map((wait) => {
    const duration = waitDuration(Math.max(0, now - Date.parse(wait.since)));
    const role = roleName(wait.role);
    return wait.name ? copy.waitingFor(wait.name, role, duration) : copy.waitingForRole(role, duration);
  });
}

/** «Fabrikk: Mikkel», «Grossist: KI-spiller», «Detaljist: Ledig», in the order the api sent
 * (Fabrikk first). */
export function seatTexts(game: OverviewGame): string[] {
  return game.seats.map((seat) => {
    const holder =
      seat.holder === "ai" ? copy.aiPlayer : seat.holder === "free" ? copy.freeSeat : (seat.name ?? copy.unknownStudent);
    return copy.seat(roleName(seat.role), holder);
  });
}

/** «1 058 kr»: the chain's Total cost so far in whole kroner; null when there is none yet. */
export function costText(game: OverviewGame): string | null {
  return game.chain_cost == null ? null : `${formatNumber(game.chain_cost, { decimals: 0 })}${KRONER}`;
}

/** «14:02:15»: a time in Europe/Oslo with seconds, for «Oppdatert». */
export function clockWithSeconds(ms: number): string {
  const parts = new Intl.DateTimeFormat("nb-NO", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date(ms));
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? "00";
  return `${part("hour")}:${part("minute")}:${part("second")}`;
}

/** The Role a wall row shows until another is chosen (Story 7.2). [ASSUMPTION: Fabrikk is the
 * default Role] */
export const DEFAULT_WALL_ROLE = "factory" as const;

const STATUS_WORD: Record<OverviewGame["status"], string> = {
  waiting: wall.status.waiting,
  running: wall.status.running,
  not_started: wall.status.notStarted,
  finished: wall.status.finished,
};

/** One Role's Netto lager per Uke from Uke 1, as the api sent it (AD-10): nothing is computed. */
export function netValues(weeks: GameWeeks | undefined, role: string): number[] {
  if (!weeks) return [];
  return weeks.weeks.flatMap((week) => {
    const seat = week.seats.find((s) => s.role === role);
    return seat ? [seat.net_inventory] : [];
  });
}

/**
 * The Matrisevegg's rows (Story 7.2, UX-DR41): the Oversikt's groups in the same order, each game
 * with «Spill n», its kjedekost in whole kroner, its status or wait after the cells, a row header
 * that reads game number, status, wait and kjedekost, and the chosen Role's Netto lager per Uke.
 * A game whose weeks have not arrived is `loading`.
 */
export function wallGroups(
  groups: readonly OverviewGroup[],
  weeks: ReadonlyMap<string, { data?: GameWeeks; failed: boolean }>,
  role: string,
  now: number,
): WallGroup[] {
  return groups.map((group) => ({
    key: group.name,
    title: `${group.title} ${group.games.length}`,
    rows: group.games.map((game): WallRow => {
      const label = copy.game(game.game_number ?? null);
      const waits = waitLines(game, now);
      const cost = costText(game);
      const status = waits.length > 0 ? waits.join("; ") : STATUS_WORD[game.status];
      const found = weeks.get(game.game_id);
      return {
        id: game.game_id,
        label,
        figure: game.chain_cost == null ? undefined : formatNumber(game.chain_cost, { decimals: 0 }),
        detail: status,
        rowName: wall.rowName([label, status.charAt(0).toLowerCase() + status.slice(1), ...(cost ? [wall.chainCost(cost)] : [])]),
        values: netValues(found?.data, role),
        loading: !found?.data && !found?.failed && game.status !== "not_started",
      };
    }),
  }));
}

/** The Oversikt table's columns beside «Spill» and the Uker (Story 7.3, UX-DR72): status, whom it
 * waits for and kjedekost, each sortable; sorting by cost is offered on this staff surface only. */
export const TABLE_COLUMNS: readonly TableColumn[] = [
  { key: "status", header: wall.table.status, first: "ascending" },
  { key: "wait", header: wall.table.waitingFor, first: "descending", wrap: true },
  { key: "cost", header: wall.figureHeader, align: "end", first: "ascending" },
];

/** The table opens in the wall's order: by status, as the groups stand. */
export const TABLE_SORT: TableSort = { key: "status", direction: "ascending" };

/** «Noah (Grossist), 23 t» for each Seat the game waits for, without «Venter på» (the column
 * header says it). */
function waitTexts(game: OverviewGame, now: number): string[] {
  return game.waiting_for.map((wait) => {
    const duration = waitDuration(Math.max(0, now - Date.parse(wait.since)));
    const role = roleName(wait.role);
    return wait.name ? wall.table.wait(wait.name, role, duration) : wall.table.waitRole(role, duration);
  });
}

/**
 * «Vis som tabell»'s rows (Story 7.3): every game of the wall's groups, in the wall's order, with
 * the same Netto lager per Uke. Each row gives the numbers its columns sort by, all as received
 * (AD-10): the game number; its place in the wall's order for status; how long its longest wait
 * has lasted at `now` (none when it waits for nobody); its chain cost (none before it starts).
 */
export function tableRows(
  groups: readonly OverviewGroup[],
  weeks: ReadonlyMap<string, { data?: GameWeeks; failed: boolean }>,
  role: string,
  now: number,
): TableRow[] {
  return groups
    .flatMap((group) => group.games)
    .map((game, index): TableRow => {
      const found = weeks.get(game.game_id);
      const since = game.waiting_for.map((wait) => Date.parse(wait.since)).filter((ms) => !Number.isNaN(ms));
      return {
        id: game.game_id,
        label: copy.game(game.game_number ?? null),
        cells: {
          status: STATUS_WORD[game.status],
          wait: waitTexts(game, now).join("; "),
          cost: game.chain_cost == null ? "" : formatNumber(game.chain_cost, { decimals: 0 }),
        },
        keys: {
          [GAME_COLUMN]: game.game_number ?? null,
          status: index,
          wait: since.length > 0 ? Math.max(0, now - Math.min(...since)) : null,
          cost: game.chain_cost == null ? null : Number(game.chain_cost),
        },
        values: netValues(found?.data, role),
        loading: !found?.data && !found?.failed && game.status !== "not_started",
      };
    });
}
