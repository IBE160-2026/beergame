import type { TableRow } from "@/components/charts/matrix-table";
import type { WallGroup } from "@/components/charts/matrix-wall";
import { nb } from "@/copy/nb";

import type { ClassGames } from "./all-games-api";
import type { Plenary, PlenaryRole } from "./plenary-api";

/**
 * «Alle spill i plenum»'s rows (Story 14.6, FR-86, UX-DR42, UX-DR72). The api sends the games in
 * game-number order and the Roles in chain order; these keep that order (no sorting, no ranking)
 * and only reshape the api's numbers for the Matrisevegg, its table and 14.5's Orders charts: the
 * web app computes nothing (AD-10). A game is keyed by its number, so focus stays on it across
 * reads.
 */
const copy = nb.plenary;

export type PlenaryView = "wall" | "table" | "orders";

/** The Role's games, or none when the api sent no such Role. */
function gamesOf(data: Plenary, role: PlenaryRole["role"]) {
  return data.roles.find((entry) => entry.role === role)?.games ?? [];
}

/** Whether any game has an opened Uke: until then there is nothing to show. */
export function hasWeeks(data: Plenary): boolean {
  return data.weeks > 0;
}

/** The wall's one group, every Class game in game-number order, its cells the Role's Netto lager. */
export function plenaryGroups(data: Plenary, role: PlenaryRole["role"]): WallGroup[] {
  const games = gamesOf(data, role);
  return [
    {
      key: "all",
      title: copy.group(games.length),
      rows: games.map((game) => ({
        id: String(game.number),
        label: nb.allGames.game(game.number),
        rowName: nb.allGames.game(game.number),
        values: game.net,
      })),
    },
  ];
}

/** «Vis som tabell»: the same rows, no extra column and nothing to sort by. */
export function plenaryTableRows(data: Plenary, role: PlenaryRole["role"]): TableRow[] {
  return gamesOf(data, role).map((game) => ({
    id: String(game.number),
    label: nb.allGames.game(game.number),
    cells: {},
    keys: {},
    values: game.net,
  }));
}

/** 14.5's Orders charts take games with an `own` mark: in plenum no game is anyone's own. */
export function plenaryOrders(data: Plenary): Pick<ClassGames, "weeks" | "roles"> {
  return {
    weeks: data.weeks,
    roles: data.roles.map((entry) => ({
      role: entry.role,
      games: entry.games.map((game) => ({ number: game.number, own: false, orders: game.orders })),
    })),
  };
}
