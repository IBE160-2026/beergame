import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { formatNumber } from "@/lib/number-format";

import { MatrixTable, type TableRow } from "./matrix-table";
import { keepOrder, nextRow, nextSort, sortRows } from "./matrix-table-sort";

const row = (id: string, keys: TableRow["keys"], values: number[] = []): TableRow => ({
  id,
  label: `Spill ${id}`,
  cells: { status: "Pågår" },
  keys,
  values,
});

describe("«Vis som tabell»'s sort (Story 7.3, UX-DR72)", () => {
  const rows = [row("a", { cost: 300 }), row("b", { cost: null }), row("c", { cost: 100 }), row("d", { cost: 300 })];

  it("sorts by the numbers given, either way, rows without one last, equal rows as they came", () => {
    expect(sortRows(rows, { key: "cost", direction: "ascending" }).map((r) => r.id)).toEqual(["c", "a", "d", "b"]);
    expect(sortRows(rows, { key: "cost", direction: "descending" }).map((r) => r.id)).toEqual(["a", "d", "c", "b"]);
    expect(sortRows(rows, null).map((r) => r.id)).toEqual(["a", "b", "c", "d"]);
  });

  it("sorts a new column its first way, and the sorted one the other way", () => {
    expect(nextSort(null, { key: "wait", first: "descending" })).toEqual({ key: "wait", direction: "descending" });
    expect(nextSort({ key: "cost", direction: "ascending" }, { key: "wait", first: "descending" })).toEqual({
      key: "wait",
      direction: "descending",
    });
    expect(nextSort({ key: "cost", direction: "ascending" }, { key: "cost", first: "ascending" })).toEqual({
      key: "cost",
      direction: "descending",
    });
  });

  it("moves Up and Down to the game above or below, staying put at an edge", () => {
    expect(nextRow(["a", "b", "c"], "b", "ArrowUp")).toBe("a");
    expect(nextRow(["a", "b", "c"], "b", "ArrowDown")).toBe("c");
    expect(nextRow(["a", "b", "c"], "a", "ArrowUp")).toBe("a");
    expect(nextRow(["a", "b", "c"], "c", "ArrowDown")).toBe("c");
    expect(nextRow(["a", "b", "c"], "b", "ArrowLeft")).toBeNull();
    expect(nextRow(["a"], "x", "ArrowDown")).toBeNull();
  });

  it("keeps the rows in place while focused: a gone row is dropped, a new one comes last", () => {
    const sorted = [row("c", {}), row("e", {}), row("a", {})];
    expect(keepOrder(["a", "b", "c"], sorted).map((r) => r.id)).toEqual(["a", "c", "e"]);
  });
});

describe("the MatrixTable HTML", () => {
  const html = renderToStaticMarkup(
    <MatrixTable
      rows={[
        { ...row("7", { game: 7, cost: null }, [4]), cells: { status: "Pågår", cost: "" } },
        { ...row("9", { game: 9, cost: 200 }), loading: true },
        { ...row("2", { game: 2, cost: 1058 }, [-13, 0, 8]), cells: { status: "Venter", cost: "1 058" } },
      ]}
      columns={[
        { key: "status", header: "Status", first: "ascending" },
        { key: "cost", header: "Kjedekost, kr", align: "end", first: "ascending" },
      ]}
      copy={{ region: "Alle spill", caption: "Netto lager for Fabrikk per uke i alle spill", gameHeader: "Spill", week: "Uke" }}
      format={(value) => formatNumber(value)}
      gameFirst="ascending"
      initialSort={{ key: "cost", direction: "descending" }}
    />,
  );

  it("is a captioned table in one named, focusable scroll region, at the table-cell size", () => {
    expect(html).toMatch(/^<div role="region" aria-label="Alle spill" tabindex="0"/);
    expect(html).toContain('<caption class="sr-only">Netto lager for Fabrikk per uke i alle spill</caption>');
    expect(html).toContain("text-table-cell");
    expect(html).toContain("lg:text-table-cell-laptop");
    expect(html).not.toMatch(/text-\[(\d|1[0-2])px\]/);
  });

  it("heads every Uke and every game, with the game column and the header row sticky", () => {
    expect(html.match(/<th scope="col"/g)).toHaveLength(3 + 3);
    expect(html).toContain('<span class="sr-only">Uke </span>3</th>');
    expect(html.match(/<th scope="row"/g)).toHaveLength(3);
    expect(html).toMatch(/<th scope="row" data-game="2" tabindex="0" class="[^"]*sticky left-0/);
    expect(html).toMatch(/<th scope="col" data-column="game" class="[^"]*sticky top-0[^"]*left-0/);
  });

  it("prints the signed number in every cell that has one, blank where the game has no such Uke", () => {
    expect(html).toContain('<td data-week="1" class="border-b border-hairline px-[0.5em] align-middle min-w-[2.75em] text-right whitespace-nowrap">−13</td>');
    expect(html).toContain(">0</td>");
    expect(html).toContain(">8</td>");
    expect(html.match(/data-week="2"[^>]*><\/td>/g)).toHaveLength(1); // Spill 7 has only Uke 1
    expect(html).toMatch(/<td colspan="3"[^>]*><div aria-hidden="true" data-skeleton=""/i);
  });

  it("marks the sorted header with aria-sort, sorts by it, keeps rows without a number last", () => {
    expect(html.match(/aria-sort=/g)).toHaveLength(1);
    expect(html).toMatch(/<th scope="col" aria-sort="descending" data-column="cost"/);
    const order = [...html.matchAll(/data-row="(\w+)"/g)].map((m) => m[1]);
    expect(order).toEqual(["2", "9", "7"]);
    expect(html.match(/<button type="button"/g)).toHaveLength(3);
  });

  it("puts one row header in the Tab order: the first row's, else the shared game's", () => {
    expect(html.match(/tabindex="0"/g)).toHaveLength(2); // the region and one row header
    const shared = renderToStaticMarkup(
      <MatrixTable
        rows={[row("a", {}), row("b", {})]}
        columns={[]}
        copy={{ region: "Alle spill", caption: "t", gameHeader: "Spill", week: "Uke" }}
        format={String}
        focusId="b"
      />,
    );
    expect(shared).toContain('data-game="b" tabindex="0"');
    expect(shared).toContain('data-game="a" tabindex="-1"');
  });
});

describe("opening a game from the table (Story 7.7)", () => {
  const render = (onActivate?: (id: string) => void) =>
    renderToStaticMarkup(
      <MatrixTable
        rows={[row("7", { game: 7 }, [4])]}
        columns={[]}
        copy={{ region: "Alle spill", caption: "c", gameHeader: "Spill", week: "Uke" }}
        format={(value) => formatNumber(value)}
        onActivate={onActivate}
      />,
    );

  it("makes each game row a click target only when the caller opens games", () => {
    expect(render(() => {})).toContain('<tr data-row="7" class="cursor-pointer">');
    expect(render()).not.toContain("cursor-pointer");
  });
});
