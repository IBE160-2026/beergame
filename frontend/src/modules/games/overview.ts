import { nb } from "@/copy/nb";
import { formatNumber, KRONER } from "@/lib/number-format";
import { roleName } from "@/modules/sessions/sessions";

import type { ClassOverview, OverviewGame } from "./api";
import { waitDuration } from "./seat-status";

const copy = nb.overview;

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
