import { nb } from "@/copy/nb";
import { formatNumber, KRONER } from "@/lib/number-format";
import { messagePath } from "@/modules/identity/homes";
import { osloWeekdayTime } from "@/modules/sessions/dates";
import { roleName } from "@/modules/sessions/sessions";

import type { WallSummary } from "@/components/charts/matrix-median";
import { GAME_COLUMN, type TableColumn, type TableFooterRow, type TableRow } from "@/components/charts/matrix-table";
import type { TableSort } from "@/components/charts/matrix-table-sort";
import type { WallGroup, WallLink, WallRow } from "@/components/charts/matrix-wall";

import type { ClassOverview, GameWeeks, OverviewGame, WallAggregates, WallFilter } from "./api";
import { markWords } from "./insight";
import { waitDuration } from "./seat-status";
import type { WallCells, WallRole } from "./wall-copy";

const copy = nb.overview;
const wall = nb.wall;

export type GroupName = "waiting" | "paused" | "running" | "notStarted" | "finished";
export type OverviewGroup = { name: GroupName; title: string; games: OverviewGame[] };

/** «41 ferdig · 15 pågår (herav 2 pauset) · 4 venter», with «· 3 ikke startet» only when some have
 * not started (FR-39) and «(herav n pauset)» only when some are paused (Story 8.6). The counts are
 * the api's; nothing here counts Weeks or hints at a game's length. */
export function headline(counts: ClassOverview["counts"]): string {
  const running =
    counts.paused > 0 ? copy.counts.runningPaused(counts.running, counts.paused) : copy.counts.running(counts.running);
  const parts = [copy.counts.finished(counts.finished), running, copy.counts.waiting(counts.waiting)];
  if (counts.not_started > 0) parts.push(copy.counts.notStarted(counts.not_started));
  return parts.join(" · ");
}

const time = (iso: string | null | undefined) => (iso ? Date.parse(iso) : Number.POSITIVE_INFINITY);
const cost = (game: OverviewGame) => (game.chain_cost == null ? Number.POSITIVE_INFINITY : Number(game.chain_cost));
const number = (game: OverviewGame) => game.game_number ?? Number.POSITIVE_INFINITY;

/** The rows the api sent, grouped by status in the order Venter, Pause, Pågår, Ikke startet,
 * Ferdig, each header with its count (UX-DR40; Pause from Story 8.6, so a paused game never drops
 * out). Venter puts the longest wait first, Pause the one paused longest, Ferdig the lowest chain
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
    {
      name: "paused",
      title: copy.groups.paused,
      games: pick("paused").sort((a, b) => time(a.paused_at) - time(b.paused_at) || byNumber(a, b)),
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

/**
 * How many changes wait while «Oppdater automatisk» is off (Story 7.5, UX-DR44): the games the
 * latest answer adds, drops or brings with another `version` than the held one. An answer that
 * differs in something else only (a name, the Start date) counts as one. Counts what it received;
 * nothing is derived from the games' contents (AD-10).
 */
export function changedGames(held: ClassOverview, latest: ClassOverview, sameAnswer: boolean): number {
  if (sameAnswer) return 0;
  const before = new Map(held.items.map((game) => [game.game_id, game.version]));
  let changed = 0;
  for (const game of latest.items) {
    if (before.get(game.game_id) !== game.version) changed += 1;
    before.delete(game.game_id);
  }
  changed += before.size;
  return Math.max(changed, 1);
}

/**
 * When (ms on the browser's clock) to read the Oversikt again for its `next_change_at` (Story 7.5,
 * AD-8): the wait the api's own clock gives, `next_change_at − server_now`, counted from the
 * answer's arrival, plus 1 s so the api finds the moment passed. The browser's clock only measures.
 */
export function readAgainAt(nextChangeAt: string, serverNow: string, receivedAt: number): number {
  return receivedAt + Date.parse(nextChangeAt) - Date.parse(serverNow) + 1_000;
}

/** The groups as they stood (by name and game id, in order), for `holdGroups`. */
export type HeldOrder = readonly { name: GroupName; ids: readonly string[] }[];

export function orderOf(groups: readonly OverviewGroup[]): HeldOrder {
  return groups.map((group) => ({ name: group.name, ids: group.games.map((game) => game.game_id) }));
}

/**
 * The groups with their rows where they stood in `held`, carrying the latest values (Story 7.5,
 * EXPERIENCE.md → Oppdater automatisk): while keyboard focus is inside the wall no row moves or
 * re-sorts, even one whose status changed. A game that left is dropped (and a group left empty
 * with it); a new game `admit` lets in goes at the end of its own group when that group stood,
 * else into a group of its own after the held ones, in `groups`' order.
 */
export function holdGroups(
  groups: readonly OverviewGroup[],
  held: HeldOrder,
  admit: (game: OverviewGame) => boolean = () => true,
): OverviewGroup[] {
  const latest = new Map(groups.flatMap((group) => group.games.map((game) => [game.game_id, game] as const)));
  const placed = new Set(held.flatMap((group) => group.ids));
  const kept = held.map((group) => ({
    name: group.name,
    title: groups.find((g) => g.name === group.name)?.title ?? titleOf(group.name),
    games: group.ids.flatMap((id) => {
      const game = latest.get(id);
      return game ? [game] : [];
    }),
  }));
  const extra: OverviewGroup[] = [];
  for (const group of groups) {
    const fresh = group.games.filter((game) => !placed.has(game.game_id) && admit(game));
    if (fresh.length === 0) continue;
    const home = kept.find((g) => g.name === group.name);
    if (home) home.games.push(...fresh);
    else extra.push({ ...group, games: fresh });
  }
  return [...kept, ...extra].filter((group) => group.games.length > 0);
}

function titleOf(name: GroupName): string {
  return copy.groups[name];
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

/** What a game's row says beside its numbers: «Venter på …» per Seat it waits for (`waitLines`),
 * or, while it is paused, «Pause siden ma. 14:10, satt av Sara.» (Story 8.6): since when and by
 * whom, in Europe/Oslo, from the api's `paused_at` and name. */
export function statusLines(game: OverviewGame, now: number): string[] {
  if (game.status === "paused" && game.paused_at) {
    return [copy.pausedSince(osloWeekdayTime(game.paused_at), game.paused_by ?? null)];
  }
  return waitLines(game, now);
}

/** «23 t»: how long the game's longest wait has lasted at `now` (its earliest `since`). */
function longestWait(game: OverviewGame, now: number): string {
  const since = Math.min(...game.waiting_for.map((wait) => Date.parse(wait.since)).filter((ms) => !Number.isNaN(ms)));
  return waitDuration(Number.isFinite(since) ? Math.max(0, now - since) : 0);
}

/** «Fabrikk: Mikkel», «Grossist: KI-spiller», «Detaljist: Ledig», in the order the api sent
 * (Fabrikk first); an AI player with a mark says why it holds the Seat, in text (Story 8.3,
 * FR-34): «Grossist: KI-spiller (KI tok over etter ventetiden)». */
export function seatTexts(game: OverviewGame): string[] {
  return game.seats.map((seat) => {
    const role = roleName(seat.role);
    if (seat.holder === "ai" && seat.mark) return copy.seatMarked(role, copy.aiPlayer, markWords(seat.mark, seat.mark_by));
    const holder =
      seat.holder === "ai" ? copy.aiPlayer : seat.holder === "free" ? copy.freeSeat : (seat.name ?? copy.unknownStudent);
    return copy.seat(role, holder);
  });
}

/** «Grossist: KI tok over etter ventetiden» for each AI-held Seat with a mark (Story 8.3): the
 * wall row's note names the Takeover and its reason in text. */
export function seatMarks(game: OverviewGame): string[] {
  return game.seats.flatMap((seat) => (seat.holder === "ai" && seat.mark ? [copy.seatMark(roleName(seat.role), markWords(seat.mark, seat.mark_by))] : []));
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

/** The Veggfiltre the Oversikt opens with (Story 7.4): Fabrikk, Netto lager, every game. */
export const DEFAULT_WALL_FILTER: WallFilter = { role: DEFAULT_WALL_ROLE, cells: "net", status: "all" };

const STATUS_WORD: Record<OverviewGame["status"], string> = {
  waiting: wall.status.waiting,
  paused: wall.status.paused,
  running: wall.status.running,
  not_started: wall.status.notStarted,
  finished: wall.status.finished,
};

/** One Role's Netto lager per Uke from Uke 1, as the api sent it (AD-10): nothing is computed. */
export function netValues(weeks: GameWeeks | undefined, role: string): number[] {
  return cellValues(weeks, role, "net");
}

/**
 * One Role's cell values per Uke from Uke 1, as the api sent them (Story 7.4, AD-10): Netto lager,
 * the Order (up to the first Uke without one: the open Week's Order may not be placed yet) or Kost
 * per uke (its decimal string read as a number to draw it). Nothing is computed.
 */
export function cellValues(weeks: GameWeeks | undefined, role: string, cells: WallCells): number[] {
  if (!weeks) return [];
  const values: number[] = [];
  for (const week of weeks.weeks) {
    const seat = week.seats.find((s) => s.role === role);
    if (!seat) break;
    const value = cells === "net" ? seat.net_inventory : cells === "order" ? seat.order : Number(seat.cost);
    if (value == null || Number.isNaN(value)) break;
    values.push(value);
  }
  return values;
}

/** The Status filter's choices (Story 7.4): every game, one status, or games with an AI player. */
export type StatusFilter = WallFilter["status"];

const hasAi = (game: OverviewGame) => game.seats.some((seat) => seat.holder === "ai");

/** The Status filter a group answers to: a paused game is one that runs, so «Pågår» takes it
 * (Story 8.6, «15 pågår (herav 2 pauset)»). */
const GROUP_STATUS: Record<GroupName, StatusFilter> = {
  waiting: "waiting",
  paused: "running",
  running: "running",
  notStarted: "not_started",
  finished: "finished",
};

/** The groups with only the games `status` matches; groups left empty are dropped. Filters the
 * rows already received and fetches nothing (AD-10). */
export function filterGroups(groups: readonly OverviewGroup[], status: StatusFilter): OverviewGroup[] {
  if (status === "all") return [...groups];
  return groups
    .map((group) => ({
      ...group,
      games: group.games.filter((game) => (status === "with_ai" ? hasAi(game) : GROUP_STATUS[group.name] === status)),
    }))
    .filter((group) => group.games.length > 0);
}

/** How many received games each Status choice matches («Venter 4», «Med KI-spiller 17»). */
export function statusCounts(games: readonly OverviewGame[]): Record<StatusFilter, number> {
  const count = (status: OverviewGame["status"]) => games.filter((game) => game.status === status).length;
  return {
    all: games.length,
    waiting: count("waiting"),
    running: count("running") + count("paused"),
    not_started: count("not_started"),
    finished: count("finished"),
    with_ai: games.filter(hasAi).length,
  };
}

/** The Varselbånd's game as the api named it (Story 7.11); null when nothing waits. */
export type OverviewAlert = ClassOverview["alert"];

/**
 * What a row offers beside its numbers (Story 7.11, UX-DR41): «Melding» to its Class game, and the
 * tint of the Varselbånd's game, named by the api (`alertId`).
 */
export type RowActions = { sessionId: string; alertId: string | null };

/** A row's «Melding»: the Meldingsskjema preset to that Class game. */
export function messageLink(sessionId: string, game: OverviewGame): WallLink {
  return {
    href: messagePath(sessionId, { game: game.game_id }),
    text: nb.messages.toGame,
    name: nb.messages.toGameLabel(game.game_number ?? null),
  };
}

/**
 * The Varselbånd's line (Stories 7.11 and 8.3, UX-DR45): «Spill 2 venter på Noah (Grossist) i 23 t.
 * KI overtar om 1 t.», the wait counted from the api's `since` and the countdown to its
 * `takeover_due_at`, both at `now` (ms on the server's clock, AD-20); «KI overtar nå.» once the due
 * time has passed, and no countdown when the api sent none. A Student no longer in the Class is
 * named by Role.
 */
export function bandText(alert: NonNullable<OverviewAlert>, now: number): string {
  const duration = waitDuration(Math.max(0, now - Date.parse(alert.since)));
  const waiting = copy.band.text(copy.game(alert.game_number ?? null), alert.name, roleName(alert.role), duration);
  const due = alert.takeover_due_at ? Date.parse(alert.takeover_due_at) : Number.NaN;
  if (Number.isNaN(due)) return waiting;
  const left = due - now;
  return `${waiting} ${left > 0 ? copy.band.takeover(waitDuration(left)) : copy.band.takeoverNow}`;
}

/** What is announced when the band appears or names another game or Student: the line without
 * its duration, so the clock alone never announces it («Spill 2 venter på Noah (Grossist).»). */
export function bandSaid(alert: OverviewAlert): string {
  return alert ? copy.band.said(copy.game(alert.game_number ?? null), alert.name, roleName(alert.role)) : "";
}

/** «Send Melding»: the Meldingsskjema preset to the Student waited for, else to the Class game. */
export function bandMessagePath(sessionId: string, alert: NonNullable<OverviewAlert>): string {
  return messagePath(sessionId, alert.user_id ? { game: alert.game_id, student: alert.user_id } : { game: alert.game_id });
}

/**
 * The Matrisevegg's rows (Story 7.2, UX-DR41): the Oversikt's groups in the same order, each game
 * with «Spill n», its kjedekost in whole kroner, its status or wait after the cells, a row header
 * that reads game number, status, wait and kjedekost, and the chosen Role's cell values per Uke
 * (Netto lager unless another is chosen, Story 7.4). A game whose weeks have not arrived is
 * `loading`.
 */
export function wallGroups(
  groups: readonly OverviewGroup[],
  weeks: ReadonlyMap<string, { data?: GameWeeks; failed: boolean }>,
  role: string,
  now: number,
  cells: WallCells = "net",
  actions?: RowActions,
): WallGroup[] {
  return groups.map((group) => ({
    key: group.name,
    title: `${group.title} ${group.games.length}`,
    rows: group.games.map((game): WallRow => {
      const label = copy.game(game.game_number ?? null);
      const waits = statusLines(game, now);
      const cost = costText(game);
      const status = [...(waits.length > 0 ? waits : [STATUS_WORD[game.status]]), ...seatMarks(game)].join("; ");
      const found = weeks.get(game.game_id);
      return {
        id: game.game_id,
        label,
        figure: game.chain_cost == null ? undefined : formatNumber(game.chain_cost, { decimals: 0 }),
        detail: status,
        shortDetail: game.waiting_for.length > 0 ? copy.waitingShort(longestWait(game, now)) : STATUS_WORD[game.status],
        rowName: wall.rowName([label, status.charAt(0).toLowerCase() + status.slice(1), ...(cost ? [wall.chainCost(cost)] : [])]),
        values: cellValues(found?.data, role, cells),
        loading: !found?.data && !found?.failed && game.status !== "not_started",
        ...rowExtras(game, actions),
      };
    }),
  }));
}

function rowExtras(game: OverviewGame, actions: RowActions | undefined): { tint?: boolean; link?: WallLink } {
  if (!actions) return {};
  return { tint: game.game_id === actions.alertId, link: messageLink(actions.sessionId, game) };
}

/** A median or quartile as read and in the table: up to one decimal («12,5», «−3»). */
const oneDecimal = (value: string) => formatNumber(value, { decimals: 1, narrow: true });
/** In a 9 px wall cell, on the graph's axis and for a mean in kroner: whole numbers. */
const whole = (value: string | number) => formatNumber(value, { decimals: 0 });

type AggregateWeek = WallAggregates["weeks"][number];
const spread = (week: AggregateWeek) =>
  week.median != null && week.lower_quartile != null && week.upper_quartile != null
    ? { median: week.median, low: week.lower_quartile, high: week.upper_quartile }
    : null;

/**
 * The class median graph and the rows «Median, Fabrikk» and «Kjedekost/uke, snitt» under the wall
 * (Story 7.4, UX-DR40, UX-DR41), only from the api's aggregates (AD-10): each Uke's printed
 * number, its name as read, and the graph's median and middle half. A Uke no game has a value
 * for has no point and no cell.
 */
export function wallSummary(aggregates: WallAggregates, role: WallRole): WallSummary {
  // No game has reached a Uke (none matched, or none has started): no graph and no empty rows.
  if (aggregates.weeks.length === 0) return { graph: [], tick: whole, rows: [] };
  return {
    graph: aggregates.weeks.map((week) => {
      const found = spread(week);
      return found ? { median: Number(found.median), low: Number(found.low), high: Number(found.high) } : null;
    }),
    tick: whole,
    rows: [
      {
        key: "median",
        label: wall.median.row(roleName(role)),
        cells: aggregates.weeks.map((week) => {
          const found = spread(week);
          return found
            ? {
                text: whole(found.median),
                name: wall.median.cell(week.week, oneDecimal(found.median), oneDecimal(found.low), oneDecimal(found.high), week.games),
              }
            : null;
        }),
      },
      {
        key: "chain",
        label: wall.median.chainRow,
        cells: aggregates.weeks.map((week) =>
          week.chain_cost_mean != null
            ? { text: whole(week.chain_cost_mean), name: wall.median.chainCell(week.week, whole(week.chain_cost_mean)) }
            : null,
        ),
      },
    ],
  };
}

/** The same two rows in the table's foot: the median to one decimal, the mean in whole kroner. */
export function tableFooter(aggregates: WallAggregates, role: WallRole): TableFooterRow[] {
  if (aggregates.weeks.length === 0) return [];
  return [
    {
      key: "median",
      label: wall.median.row(roleName(role)),
      values: aggregates.weeks.map((week) => (week.median != null ? oneDecimal(week.median) : null)),
    },
    {
      key: "chain",
      label: wall.median.chainRow,
      values: aggregates.weeks.map((week) => (week.chain_cost_mean != null ? whole(week.chain_cost_mean) : null)),
    },
  ];
}

/** The Oversikt table's columns beside «Spill» and the Uker (Story 7.3, UX-DR72): status, whom it
 * waits for and kjedekost, each sortable; sorting by cost is offered on this staff surface only. */
export const TABLE_COLUMNS: readonly TableColumn[] = [
  { key: "status", header: wall.table.status, first: "ascending" },
  { key: "wait", header: wall.table.waitingFor, first: "descending" },
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
 * the same cell values per Uke. Each row gives the numbers its columns sort by, all as received
 * (AD-10): the game number; its place in the wall's order for status; how long its longest wait
 * has lasted at `now` (none when it waits for nobody); its chain cost (none before it starts).
 */
export function tableRows(
  groups: readonly OverviewGroup[],
  weeks: ReadonlyMap<string, { data?: GameWeeks; failed: boolean }>,
  role: string,
  now: number,
  cells: WallCells = "net",
  actions?: RowActions,
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
        values: cellValues(found?.data, role, cells),
        loading: !found?.data && !found?.failed && game.status !== "not_started",
        ...rowExtras(game, actions),
      };
    });
}

const rail = copy.rail;

/** One game in «Venter ellers»: «Spill 30» and «Ida, Detaljist, 18 t» per Seat it waits for. */
export type WaitingRow = { id: string; game: string; who: string[] };

/**
 * «Venter ellers» (Story 7.6, UX-DR40): the waiting games as the Venter group orders them, longest
 * wait first, each with whom it waits for and for how long at `now`, leaving out the Varselbånd's
 * game (`alertId`, Story 7.11, UX-DR45). Reads the groups it is given.
 */
export function waitingElsewhere(groups: readonly OverviewGroup[], now: number, alertId: string | null = null): WaitingRow[] {
  const waiting = groups.find((group) => group.name === "waiting")?.games ?? [];
  return waiting.filter((game) => game.game_id !== alertId).map((game) => ({
    id: game.game_id,
    game: copy.game(game.game_number ?? null),
    // A waiting game with no named wait (none has a start time) still reads as waiting.
    who: game.waiting_for.length === 0 ? [wall.status.waiting] : game.waiting_for.map((wait) => {
      const duration = waitDuration(Math.max(0, now - Date.parse(wait.since)));
      const role = roleName(wait.role);
      return wait.name ? rail.waiting.who(wait.name, role, duration) : rail.waiting.whoRole(role, duration);
    }),
  }));
}

/** «22 KI-spillere i 17 spill, alle merket.» from the api's counts (UX-DR69). */
export function aiLine(ai: ClassOverview["ai"]): string {
  return rail.waiting.ai(ai.seats, ai.games);
}

export type ClassCost = NonNullable<ClassOverview["cost"]>;

/** «Median 1 954. Midterste halvdel 1 500–2 600.»: the api's median and quartiles in whole
 * kroner (EXPERIENCE.md → Charts). */
export function costSummary(cost: ClassCost): string {
  return rail.cost.summary(whole(cost.median), whole(cost.lower_quartile), whole(cost.upper_quartile));
}

/** The Kostnadsfordeling's table: every finished game with its chain cost, lowest first. */
export function costRows(games: readonly OverviewGame[]): { id: string; game: string; cost: string; value: number }[] {
  return games
    .filter((game) => game.status === "finished" && game.chain_cost != null)
    .map((game) => ({
      id: game.game_id,
      game: copy.game(game.game_number ?? null),
      cost: whole(game.chain_cost!),
      value: Number(game.chain_cost),
    }))
    .sort((a, b) => a.value - b.value || a.game.localeCompare(b.game, "nb", { numeric: true }));
}

/** One Role's bar in «Snitt per ferdig spill, per Rolle»: its parts as shares of the longest bar. */
export type RoleBar = { role: string; name: string; amount: string; holding: number; backorder: number; reads: string };

/**
 * «Snitt per ferdig spill, per Rolle» (UX-DR72): per Role, Detaljist first, the api's mean lager and
 * restordre drawn as shares of the costliest Role's total, with the total printed in whole kroner.
 * The shares only scale the bars (AD-10).
 */
export function roleBars(cost: ClassCost): RoleBar[] {
  const longest = Math.max(0, ...cost.roles.map((role) => Number(role.total_cost)));
  const share = (value: string) => (longest > 0 ? Number(value) / longest : 0);
  return cost.roles.map((role) => {
    const name = roleName(role.role);
    return {
      role: role.role,
      name,
      amount: whole(role.total_cost),
      holding: share(role.holding_cost),
      backorder: share(role.backorder_cost),
      reads: rail.cost.roleName(name, whole(role.holding_cost), whole(role.backorder_cost), whole(role.total_cost)),
    };
  });
}

/** One stage of the Trakt: its name, its count and its bar as a share of the largest count. */
export type FunnelRow = { stage: string; label: string; count: number; share: number };

/** The Trakt's stages in the api's order with their counts (FR-39); the shares only scale the
 * `aria-hidden` bars. */
export function funnelRows(funnel: ClassOverview["funnel"]): FunnelRow[] {
  const most = Math.max(0, ...funnel.map((stage) => stage.count));
  return funnel.map((stage) => ({
    stage: stage.stage,
    label: rail.funnel.stages[stage.stage],
    count: stage.count,
    share: most > 0 ? stage.count / most : 0,
  }));
}
