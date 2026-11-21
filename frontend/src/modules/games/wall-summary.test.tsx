import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { MatrixTable } from "@/components/charts/matrix-table";
import { MatrixWall } from "@/components/charts/matrix-wall";
import { GROUP, MINUS } from "@/lib/number-format";

import type { WallAggregates } from "./api";
import fixture from "./fixtures/wall-aggregates.json";
import { tableFooter, wallSummary } from "./overview";
import { formatCell, wallCopy } from "./wall-copy";

/** The api's answer for Fabrikk, Netto lager, every game: 3 games, Uke 4 without a median. */
const AGGREGATES = fixture as WallAggregates;

describe("the class median rows from the api's aggregates (Story 7.4, AD-10)", () => {
  const summary = wallSummary(AGGREGATES, "factory");

  it("takes the graph's median and middle half per Uke as sent, none where no game has a value", () => {
    expect(summary.graph).toEqual([
      { median: 12, low: 12, high: 12 },
      { median: 8.5, low: 4.25, high: 10 },
      { median: -16, low: -27, high: -4 },
      null,
    ]);
  });

  it("prints whole numbers in the wall's rows and reads the exact median, middle half and games", () => {
    const [median, chain] = summary.rows;
    expect(median!.label).toBe("Median, Fabrikk");
    expect(median!.cells.map((cell) => cell?.text ?? null)).toEqual(["12", "9", `${MINUS}16`, null]);
    expect(median!.cells[1]!.name).toBe("Uke 2: median 8,5, midterste halvdel 4,3 til 10, 3 spill.");
    expect(chain!.label).toBe("Kjedekost/uke, snitt");
    expect(chain!.cells.map((cell) => cell?.text)).toEqual(["24", "27", "66", "102"]);
    expect(chain!.cells[3]!.name).toBe("Uke 4: kjedekost per uke, snitt 102 kr.");
  });

  it("renders the graph over the wall and both rows under it, each cell named", () => {
    const html = renderToStaticMarkup(
      <MatrixWall
        width={600}
        fontSize={13}
        copy={wallCopy("factory", true)}
        format={formatCell}
        summary={summary}
        groups={[{ key: "g", title: "Pågår 1", rows: [{ id: "g1", label: "Spill 1", rowName: "Spill 1", values: [12, 4, -30] }] }]}
      />,
    );
    expect(html).toContain('data-median-graph=""');
    expect(html).toMatch(/<g aria-hidden="true" data-median-graph="">/);
    expect(html.match(/<polygon/g)).toHaveLength(1); // Uke 1–3 in one run; Uke 4 has no point
    expect(html).toContain('data-summary="median"');
    expect(html).toContain('data-summary="chain"');
    expect(html).toContain('role="rowheader" aria-colindex="1"');
    expect(html).toContain('aria-label="Uke 3: median −16, midterste halvdel −27 til −4, 2 spill."');
    expect(html).toContain('aria-label="Uke 4: kjedekost per uke, snitt 102 kr."');
    // Four Uker: the wall's columns reach the rows' last Uke, though the game has three.
    expect(html.match(/role="columnheader"/g)).toHaveLength(5);
    expect(html).toContain('aria-rowcount="5"'); // header, group, game, two summary rows
    expect(html).toContain(`>${MINUS}16</text>`);
  });

  it("puts the same rows in the table's foot: the median to one decimal, the mean in whole kroner", () => {
    const footer = tableFooter(AGGREGATES, "factory");
    expect(footer.map((row) => [row.label, row.values])).toEqual([
      ["Median, Fabrikk", ["12", "8,5", `${MINUS}16`, null]],
      ["Kjedekost/uke, snitt", ["24", "27", "66", "102"]],
    ]);
    const html = renderToStaticMarkup(
      <MatrixTable
        rows={[{ id: "g1", label: "Spill 1", cells: {}, keys: {}, values: [1_000, 2] }]}
        columns={[]}
        copy={{ region: "Alle spill", caption: "c", gameHeader: "Spill", week: "Uke" }}
        format={formatCell}
        footer={footer}
      />,
    );
    expect(html).toContain("<tfoot>");
    expect(html).toMatch(/<tfoot>.*<th scope="row"[^>]*>Median, Fabrikk<\/th>/);
    expect(html).toContain(`1${GROUP}000`);
    expect(html).toContain("min-w-full");
    expect(html.match(/<th scope="col"/g)).toHaveLength(5); // Spill + Uke 1–4
  });
});

describe("the class median at the edges (Story 7.4 review)", () => {
  it("has no graph and no rows when no game has reached a Uke", () => {
    const none = { ...AGGREGATES, games: 0, weeks: [] };
    expect(wallSummary(none, "factory")).toMatchObject({ graph: [], rows: [] });
    expect(tableFooter(none, "factory")).toEqual([]);
  });

  it("draws a lone Uke's middle half as a short band with a dot for its median", () => {
    const one = { ...AGGREGATES, weeks: AGGREGATES.weeks.slice(1, 2) };
    const html = renderToStaticMarkup(
      <MatrixWall
        width={600}
        fontSize={13}
        copy={wallCopy("factory", true)}
        format={formatCell}
        summary={wallSummary(one, "factory")}
        groups={[{ key: "g", title: "Pågår 1", rows: [{ id: "g1", label: "Spill 1", rowName: "Spill 1", values: [4] }] }]}
      />,
    );
    const band = /<polygon points="([^"]+)"/.exec(html)![1]!.split(" ").map((p) => p.split(",").map(Number));
    expect(new Set(band.map(([x]) => x)).size).toBe(2); // a width, not a line
    expect(new Set(band.map(([, y]) => y)).size).toBe(2); // from the lower to the upper quartile
    expect(html).toMatch(/<circle[^>]*data-median=""/);
  });
});
