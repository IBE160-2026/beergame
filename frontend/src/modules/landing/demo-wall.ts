import type { WallGroup, WallRow } from "@/components/charts/matrix-wall";
import { nb } from "@/copy/nb";

import demo from "./demo-wall.json";

type DemoGame = { number: number; status: "waiting" | "running"; values: number[] };

/**
 * The Landing's «Alle spillene på én skjerm» (Story 7.2, UX-DR70, UX-DR71): eight made-up Class
 * games' Fabrikk Netto lager, bundled in the web app, never read from the api. It is Demodata:
 * no names, no Uke per row, no Uke total and no finished game, so nothing tells a game's length
 * (FR-14). `demo-wall.test.ts` holds the fixture to these rules.
 */
export const DEMO_WALL_GAMES: readonly DemoGame[] = demo.games as DemoGame[];

const ORDER = ["waiting", "running"] as const;

/** The demo games as the wall's groups, Venter first, each row named «Spill n, venter». */
export function demoWallGroups(): WallGroup[] {
  return ORDER.map((status) => {
    const games = DEMO_WALL_GAMES.filter((game) => game.status === status).sort((a, b) => a.number - b.number);
    const title = status === "waiting" ? nb.overview.groups.waiting : nb.overview.groups.running;
    const word = status === "waiting" ? nb.wall.status.waiting : nb.wall.status.running;
    return {
      key: status,
      title: `${title} ${games.length}`,
      rows: games.map(
        (game): WallRow => ({
          id: `demo-${game.number}`,
          label: nb.overview.game(game.number),
          rowName: nb.wall.rowName([nb.overview.game(game.number), word.toLowerCase()]),
          values: game.values,
        }),
      ),
    };
  }).filter((group) => group.rows.length > 0);
}
