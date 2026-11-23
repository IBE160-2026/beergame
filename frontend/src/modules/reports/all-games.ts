import { orderAxisTop } from "@/components/charts/order-lines";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { ClassGames, RoleOrders } from "./all-games-api";

/**
 * «Alle spill side om side»'s text and order (Story 14.5, FR-86, UX-DR72, UX-DR73). The api sends
 * the games in game-number order and the Roles in chain order; these keep the games' order (no
 * sorting, no ranking), put Fabrikk at the top and word the own game. The only arithmetic is the
 * shared chart scale.
 */
const copy = nb.allGames;

/** Fabrikk first (UX-DR73): the api sends the chain order, Detaljist first. */
export function rolesFabrikkFirst(data: Pick<ClassGames, "roles">): RoleOrders[] {
  return [...data.roles].reverse();
}

/** One top for every Role's chart, so they read on the same scale (`09-alle-sider.png`). */
export function sharedTop(data: Pick<ClassGames, "roles">): number {
  let highest = 0;
  for (const role of data.roles) {
    for (const game of role.games) {
      for (const order of game.orders) if (order !== null && order > highest) highest = order;
    }
  }
  return orderAxisTop(highest);
}

/** The line that names the own game and how it is drawn, or says it is not listed. */
export function ownLine(data: Pick<ClassGames, "own_game">): string {
  return data.own_game === null ? copy.noOwn : copy.own(data.own_game);
}

/** «Vis som tabell»: one row per game in game-number order, a cell per Uke. */
export function tableRows(role: RoleOrders): { key: string; head: string; cells: string[] }[] {
  return role.games.map((game) => ({
    key: String(game.number),
    head: game.own ? copy.ownGame(game.number) : copy.game(game.number),
    cells: game.orders.map((order) => (order === null ? copy.noOrder : formatNumber(order, { decimals: 0 }))),
  }));
}

/** The table's columns: «Spill», then «Uke 1» … «Uke n». */
export function tableColumns(weeks: number): string[] {
  return [copy.gameColumn, ...Array.from({ length: weeks }, (_, i) => copy.week(i + 1))];
}
