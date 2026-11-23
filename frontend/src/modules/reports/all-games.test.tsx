import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { OrderLines, orderAxisTop } from "@/components/charts/order-lines";
import { nb } from "@/copy/nb";

import type { ClassGames } from "./all-games-api";
import { ownLine, rolesFabrikkFirst, sharedTop, tableColumns, tableRows } from "./all-games";

const copy = nb.allGames;

const DATA: ClassGames = {
  weeks: 3,
  own_game: 2,
  roles: (["retailer", "wholesaler", "distributor", "factory"] as const).map((role, i) => ({
    role,
    games: [
      { number: 1, own: false, orders: [4, 8 + i, null] },
      { number: 2, own: true, orders: [4, 12, 23 + i] },
      { number: 3, own: false, orders: [null, null, null] },
    ],
  })),
};

describe("«Alle spill side om side» (Story 14.5)", () => {
  it("puts Fabrikk at the top and keeps the games in game-number order", () => {
    expect(rolesFabrikkFirst(DATA).map((r) => r.role)).toEqual(["factory", "distributor", "wholesaler", "retailer"]);
    expect(rolesFabrikkFirst(DATA)[0]!.games.map((g) => g.number)).toEqual([1, 2, 3]);
  });

  it("gives every Role one axis top over the highest Order of any game", () => {
    expect(sharedTop(DATA)).toBe(30); // 26 in the Fabrikk's own game
    expect(sharedTop({ roles: [] })).toBe(10);
    expect([0, 10, 11, 40, 41].map(orderAxisTop)).toEqual([10, 10, 20, 40, 50]);
  });

  it("names the own game in text, or says it is not listed", () => {
    expect(ownLine(DATA)).toBe(copy.own(2));
    expect(ownLine({ own_game: null })).toBe(copy.noOwn);
  });

  it("lists the table by game number with the own row named and a dash for no Order", () => {
    expect(tableColumns(3)).toEqual([copy.gameColumn, "Uke 1", "Uke 2", "Uke 3"]);
    const rows = tableRows(DATA.roles[0]!);
    expect(rows.map((r) => r.head)).toEqual(["Spill 1", "Spill 2 (ditt spill)", "Spill 3"]);
    expect(rows[0]!.cells).toEqual(["4", "8", copy.noOrder]);
    expect(rows[2]!.cells).toEqual([copy.noOrder, copy.noOrder, copy.noOrder]);
  });
});

describe("Ordrelinjer (Story 14.5)", () => {
  const svg = renderToStaticMarkup(
    <OrderLines
      width={360}
      height={140}
      fontSize={13}
      top={30}
      lines={DATA.roles[3]!.games.map((g) => ({ key: String(g.number), own: g.own, orders: g.orders }))}
      title="Ordre per uke fra Fabrikk i 3 klassespill"
      formatTick={String}
      firstLabel="Uke 1"
      lastLabel="Uke 3"
    />,
  );

  it("is aria-hidden with a title, and marks the own game by stroke and points, not colour alone", () => {
    expect(svg).toContain('aria-hidden="true"');
    expect(svg).toContain("<title>Ordre per uke fra Fabrikk i 3 klassespill</title>");
    expect(svg.match(/data-mark="game-line"/g)).toHaveLength(2);
    expect(svg.match(/data-mark="own-line"/g)).toHaveLength(1);
    // A point at each of the own game's three Weeks; none on the other games.
    expect(svg.match(/<circle/g)).toHaveLength(3);
    expect(svg).toContain('stroke-width="2.5"');
  });

  it("breaks a line at a Week with no Order and draws nothing for a game with none", () => {
    const gap = renderToStaticMarkup(
      <OrderLines
        width={360}
        height={140}
        fontSize={13}
        top={10}
        lines={[
          { key: "1", own: false, orders: [4, null, 6] },
          { key: "3", own: false, orders: [null, null, null] },
        ]}
        title="t"
        formatTick={String}
        firstLabel="Uke 1"
        lastLabel="Uke 3"
      />,
    );
    const paths = [...gap.matchAll(/<path d="([^"]*)"[^>]*data-game="(\d)"/g)].map((m) => [m[2], m[1]] as const);
    expect(paths.find(([game]) => game === "1")![1].match(/M/g)).toHaveLength(2);
    expect(paths.find(([game]) => game === "3")![1]).toBe("");
  });
});
