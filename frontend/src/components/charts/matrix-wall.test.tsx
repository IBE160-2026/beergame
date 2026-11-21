import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { formatNumber } from "@/lib/number-format";

import { MatrixWall, type MatrixWallCopy } from "./matrix-wall";
import { graphScale } from "./matrix-median";
import {
  cellText,
  FLOW_STEPS,
  flowStep,
  headerWeeks,
  moveFocus,
  NET_STEPS,
  netStep,
  stepFill,
  stepText,
  wallSizes,
} from "./matrix-wall-layout";
import { colour } from "./palette";

describe("the Matrisevegg's cell rule (Story 7.2, DESIGN.md → Components → Matrisevegg)", () => {
  it("prints the signed number when it fits with 1 px to spare on each side", () => {
    // At 9 px a digit and the true minus are each at most 0.54 em: «−13» needs 15 px, «8» 5 px.
    expect(cellText(-13, "−13", 17, 9)).toEqual({ kind: "number", text: "−13" });
    expect(cellText(8, "8", 7, 9)).toEqual({ kind: "number", text: "8" });
    expect(cellText(0, "0", 15, 9)).toEqual({ kind: "number", text: "0" });
  });

  it("else prints only a centred true minus below zero, and leaves other cells blank", () => {
    expect(cellText(-13, "−13", 16, 9)).toEqual({ kind: "minus", text: "−" });
    expect(cellText(-13, "−13", 15, 9)).toEqual({ kind: "minus", text: "−" });
    expect(cellText(-120, "−120", 15, 9)).toEqual({ kind: "minus", text: "−" });
    expect(cellText(13, "13", 11, 9)).toEqual({ kind: "blank", text: "" });
    expect(cellText(0, "0", 6, 9)).toEqual({ kind: "blank", text: "" });
  });

  it("writes ink on zero and steps 1–2 and paper on steps 3–4", () => {
    expect(NET_STEPS.map((step) => [step, stepText(step)])).toEqual([
      ["neg-4", "paper"],
      ["neg-3", "paper"],
      ["neg-2", "ink"],
      ["neg-1", "ink"],
      ["zero", "ink"],
      ["pos-1", "ink"],
      ["pos-2", "ink"],
      ["pos-3", "paper"],
      ["pos-4", "paper"],
    ]);
  });

  it("bins the legend's edges as written: −35 og lavere … 35 og over", () => {
    expect([-35, -34, -20, -19, -10, -9, -1, 0, 1, 9, 10, 19, 20, 34, 35].map(netStep)).toEqual([
      "neg-4",
      "neg-3",
      "neg-3",
      "neg-2",
      "neg-2",
      "neg-1",
      "neg-1",
      "zero",
      "pos-1",
      "pos-1",
      "pos-2",
      "pos-2",
      "pos-3",
      "pos-3",
      "pos-4",
    ]);
  });
});

describe("the Matrisevegg's layout", () => {
  const base = { fontSize: 13, labels: ["Spill 12"], figures: ["12 345"], details: [] };

  it("shares the width among the Uker, at least near-square and at most two rows wide", () => {
    const wide = wallSizes({ ...base, width: 1200, columns: 36 });
    expect(wide.cellWidth).toBeGreaterThanOrEqual(Math.ceil(wide.rowHeight * 0.85));
    expect(wide.width).toBeLessThanOrEqual(1200);
    const narrow = wallSizes({ ...base, width: 288, columns: 36 });
    expect(narrow.cellWidth).toBe(Math.ceil(narrow.rowHeight * 0.85));
    expect(narrow.width).toBeGreaterThan(288); // its region scrolls, never the page
    expect(wallSizes({ ...base, width: 2000, columns: 3 }).cellWidth).toBe(wide.rowHeight * 2);
  });

  it("has no Uke column before any game has a Uke, yet room for a loading row's Skjelett", () => {
    const empty = wallSizes({ ...base, width: 900, columns: 0 });
    expect(empty.columns).toBe(0);
    expect(empty.width).toBe(empty.labelWidth + 8 * empty.cellWidth);
  });

  it("draws the short notes when a full one would run past the width, each after its own cells (Story 7.6)", () => {
    const notes = [
      { cells: 2, full: "Venter på Spiller2 0461 (Distributør), under 1 min", short: "Venter, under 1 min" },
      { cells: 5, full: "Pågår", short: "Pågår" },
    ];
    // 390 px screen: the full note does not fit; the short one does, and so does the drawing.
    const phone = wallSizes({ ...base, width: 350, columns: 5, notes });
    expect(phone.shortDetail).toBe(true);
    expect(phone.width).toBeLessThanOrEqual(350);
    // A laptop column: the full notes.
    const laptop = wallSizes({ ...base, width: 900, columns: 5, notes });
    expect(laptop.shortDetail).toBe(false);
    expect(laptop.width).toBeLessThanOrEqual(900);
    // Too many Uker for the width: the cells scroll in the region, the note is short.
    const long = wallSizes({ ...base, width: 350, columns: 36, notes: [{ ...notes[0]!, cells: 36 }] });
    expect(long.shortDetail).toBe(true);
    expect(long.width).toBe(long.labelWidth + 36 * long.cellWidth + long.detailWidth);
  });

  it("never draws cell text under 9 px, and grows it with the text", () => {
    expect(wallSizes({ ...base, width: 900, columns: 20 }).cellFont).toBe(9);
    expect(wallSizes({ ...base, fontSize: 26, width: 900, columns: 20 }).cellFont).toBe(18);
    expect(wallSizes({ ...base, fontSize: 10, width: 900, columns: 20 }).cellFont).toBe(9);
  });

  it("numbers every Uke in the header when they fit, else Uke 1 and every fifth", () => {
    expect(headerWeeks(4, 30, 13)).toEqual([1, 2, 3, 4]);
    expect(headerWeeks(12, 14, 13)).toEqual([1, 5, 10]);
  });

  it("moves focus cell by cell, between game rows, and to a row's ends", () => {
    const rows = [
      { id: "a", cells: 10 },
      { id: "empty", cells: 0 },
      { id: "b", cells: 4 },
    ];
    expect(moveFocus(rows, { id: "a", week: 3 }, "ArrowRight")).toEqual({ id: "a", week: 4 });
    expect(moveFocus(rows, { id: "a", week: 1 }, "ArrowLeft")).toEqual({ id: "a", week: 1 });
    expect(moveFocus(rows, { id: "a", week: 10 }, "ArrowRight")).toEqual({ id: "a", week: 10 });
    expect(moveFocus(rows, { id: "a", week: 9 }, "ArrowDown")).toEqual({ id: "b", week: 4 });
    expect(moveFocus(rows, { id: "b", week: 2 }, "ArrowUp")).toEqual({ id: "a", week: 2 });
    expect(moveFocus(rows, { id: "b", week: 2 }, "ArrowDown")).toEqual({ id: "b", week: 2 });
    expect(moveFocus(rows, { id: "a", week: 5 }, "Home")).toEqual({ id: "a", week: 1 });
    expect(moveFocus(rows, { id: "a", week: 5 }, "End")).toEqual({ id: "a", week: 10 });
    expect(moveFocus(rows, { id: "a", week: 5 }, "Enter")).toBeNull();
  });
});

const COPY: MatrixWallCopy = {
  region: "Alle spill",
  title: "Netto lager for Fabrikk per uke i alle spill",
  gameHeader: "Spill",
  figureHeader: "Kjedekost",
  week: (week) => `Uke ${week}`,
  cell: (row, week, value) => `${row.label}, Uke ${week}: Netto lager ${value}.`,
  bins: ["a", "b", "c", "d", "e", "f", "g", "h", "i"],
  minusNote: "− i en celle: restordre (under null).",
  legend: "Fargeskala for netto lager",
};

describe("the Matrisevegg SVG", () => {
  const html = renderToStaticMarkup(
    <MatrixWall
      width={200}
      fontSize={13}
      copy={COPY}
      format={(value) => formatNumber(value)}
      groups={[
        {
          key: "waiting",
          title: "Venter 1",
          rows: [{ id: "g2", label: "Spill 2", figure: "1 058", rowName: "Spill 2, venter, kjedekost 1 058 kr", values: [12, -13, 0, -400] }],
        },
        { key: "running", title: "Pågår 1", rows: [{ id: "g3", label: "Spill 3", rowName: "Spill 3, pågår", values: [], loading: true }] },
      ]}
    />,
  );

  it("is a named grid in one named scroll region, with Uke headers, row headers and named cells", () => {
    expect(html).toContain('role="region" aria-label="Alle spill" tabindex="0"');
    expect(html).toMatch(/<svg[^>]*role="grid"/);
    expect(html).toContain("<title");
    expect(html).not.toContain('role="grid" aria-hidden');
    expect(html.match(/role="columnheader"/g)).toHaveLength(5); // Spill + Uke 1–4
    expect(html).toContain('aria-label="Uke 4"');
    expect(html).toContain('role="rowheader" aria-label="Spill 2, venter, kjedekost 1 058 kr"');
    expect(html).toContain('aria-label="Spill 2, Uke 2: Netto lager −13."');
    expect(html.match(/role="gridcell"/g)).toHaveLength(4);
  });

  it("puts one cell in the Tab order: the first", () => {
    expect(html.match(/tabindex="0"/g)).toHaveLength(2); // the region and one cell
    expect(html).toMatch(/aria-label="Spill 2, Uke 1: Netto lager 12\." tabindex="0"/);
  });

  it("draws square cells in the matrix steps, with paper text on the dark steps", () => {
    expect(html).not.toMatch(/<rect[^>]*\brx=/);
    expect(html).toContain(`fill="${colour("net-neg-4")}"`);
    expect(html).toMatch(new RegExp(`font-size="9" fill="${colour("paper")}"[^>]*>−</text>`));
  });

  it("shows the legend with every step and the minus line, and a Skjelett bar for a loading row", () => {
    expect(html.match(/<li[ >]/g)).toHaveLength(9);
    expect(html).toContain("− i en celle: restordre (under null).");
    expect(html).toContain("data-skeleton");
  });
});

describe("the flow steps for Ordre and Kost per uke (Story 7.4, DESIGN.md → Matrix steps)", () => {
  it("leaves under 5 unfilled and bins 5–9, 10–19, 20–29 and 30+", () => {
    expect([0, 4.99, 5, 9, 10, 19.5, 20, 29, 30, 120].map(flowStep)).toEqual([
      "flow-none",
      "flow-none",
      "flow-1",
      "flow-1",
      "flow-2",
      "flow-2",
      "flow-3",
      "flow-3",
      "flow-4",
      "flow-4",
    ]);
    expect(FLOW_STEPS.map((step) => [stepFill(step), stepText(step)])).toEqual([
      ["paper", "ink"],
      ["flow-1", "ink"],
      ["flow-2", "ink"],
      ["flow-3", "paper"],
      ["flow-4", "paper"],
    ]);
  });

  it("draws the cells and the legend in the flow steps, without the minus line", () => {
    const html = renderToStaticMarkup(
      <MatrixWall
        width={200}
        fontSize={13}
        copy={{ ...COPY, bins: ["Under 5", "5 til 9", "10 til 19", "20 til 29", "30 og over"], minusNote: undefined }}
        format={(value) => formatNumber(value)}
        scale="flow"
        groups={[{ key: "g", title: "Pågår 1", rows: [{ id: "g1", label: "Spill 1", rowName: "Spill 1", values: [4, 8, 24, 40] }] }]}
      />,
    );
    expect(html).toContain('data-wall-legend="flow"');
    expect(html.match(/<li[ >]/g)).toHaveLength(5);
    expect(html).not.toContain("restordre");
    expect(html.match(/data-step="flow-[a-z0-9]+"/g)).toEqual([
      'data-step="flow-none"',
      'data-step="flow-1"',
      'data-step="flow-2"',
      'data-step="flow-3"',
      'data-step="flow-4"',
      'data-step="flow-none"',
      'data-step="flow-1"',
      'data-step="flow-3"',
      'data-step="flow-4"',
    ]);
  });
});

describe("the class median graph's scale (Story 7.4)", () => {
  it("spans the band and zero, ticks the rounded ends and zero, and drops a tick too close to zero", () => {
    const points = [{ median: -39, low: -45, high: -20 }, null, { median: 18, low: 10, high: 22 }];
    const scale = graphScale(points, 0, 100, 13);
    expect(scale.ticks).toEqual([25, 0, -45]);
    expect(scale.y(25)).toBe(0);
    expect(scale.y(-45)).toBe(100);
    expect(graphScale([{ median: 2, low: 1, high: 3 }], 0, 100, 13).ticks).toEqual([5, 0]);
  });
});

describe("opening a game from the wall (Story 7.7)", () => {
  const render = (onActivate?: (id: string) => void) =>
    renderToStaticMarkup(
      <MatrixWall
        width={200}
        fontSize={13}
        copy={COPY}
        format={(value) => formatNumber(value)}
        onActivate={onActivate}
        groups={[{ key: "running", title: "Pågår 1", rows: [{ id: "g3", label: "Spill 3", rowName: "Spill 3, pågår", values: [4] }] }]}
      />,
    );

  it("makes each game row a click target only when the caller opens games", () => {
    expect(render(() => {})).toMatch(/role="row"[^>]*data-row="g3"[^>]*class="cursor-pointer"/);
    expect(render()).not.toContain("cursor-pointer");
  });
});

describe("«Melding» in the wall and the band's tint (Story 7.11, UX-DR41)", () => {
  const link = (id: string) => ({ href: `/m/${id}`, text: "Melding", name: `Melding til alle i Spill ${id}` });

  it("reaches a row's link by Right from its last Uke, moves link to link, and a row without Uker by its link", () => {
    const rows = [
      { id: "a", cells: 3, link: true },
      { id: "new", cells: 0, link: true },
      { id: "b", cells: 2, link: true },
      { id: "plain", cells: 0 },
    ];
    expect(moveFocus(rows, { id: "a", week: 3 }, "ArrowRight")).toEqual({ id: "a", week: 3, link: true });
    expect(moveFocus(rows, { id: "a", week: 3, link: true }, "ArrowRight")).toEqual({ id: "a", week: 3, link: true });
    expect(moveFocus(rows, { id: "a", week: 3, link: true }, "ArrowLeft")).toEqual({ id: "a", week: 3 });
    expect(moveFocus(rows, { id: "a", week: 3, link: true }, "ArrowDown")).toEqual({ id: "new", week: 3, link: true });
    expect(moveFocus(rows, { id: "a", week: 2 }, "ArrowDown")).toEqual({ id: "new", week: 2, link: true });
    expect(moveFocus(rows, { id: "new", week: 2, link: true }, "ArrowDown")).toEqual({ id: "b", week: 2, link: true });
    expect(moveFocus(rows, { id: "new", week: 2, link: true }, "ArrowLeft")).toEqual({ id: "new", week: 2, link: true });
    expect(moveFocus(rows, { id: "b", week: 2, link: true }, "ArrowDown")).toEqual({ id: "b", week: 2, link: true });
    expect(moveFocus(rows, { id: "b", week: 1 }, "End")).toEqual({ id: "b", week: 2 });
    expect(moveFocus(rows, { id: "b", week: 2, link: true }, "Home")).toEqual({ id: "b", week: 1 });
  });

  it("makes room for the link column at the drawing's right edge", () => {
    const base = { width: 400, fontSize: 13, columns: 10, labels: ["Spill 12"], figures: [], details: [] };
    const without = wallSizes(base);
    const withLinks = wallSizes({ ...base, links: ["Melding"] });
    expect(without.linkWidth).toBe(0);
    expect(withLinks.linkWidth).toBeGreaterThan(0);
    expect(withLinks.linkRight).toBe(withLinks.width - 1);
    expect(withLinks.width - withLinks.linkWidth).toBeGreaterThanOrEqual(withLinks.labelWidth + 10 * withLinks.cellWidth);
  });

  const html = renderToStaticMarkup(
    <MatrixWall
      width={300}
      fontSize={13}
      copy={COPY}
      format={(value) => formatNumber(value)}
      onActivate={() => {}}
      groups={[
        {
          key: "waiting",
          title: "Venter 2",
          rows: [
            { id: "g2", label: "Spill 2", rowName: "Spill 2", values: [3, -4], tint: true, link: link("2") },
            { id: "g5", label: "Spill 5", rowName: "Spill 5", values: [1], link: link("5") },
          ],
        },
        { key: "notStarted", title: "Ikke startet 1", rows: [{ id: "g7", label: "Spill 7", rowName: "Spill 7", values: [], link: link("7") }] },
      ]}
    />,
  );

  it("gives every row its link as the last grid cell, out of the Tab order, ink on the tinted row and lager elsewhere", () => {
    expect(html.match(/<a [^>]*data-link=""/g)).toHaveLength(3);
    expect(html).toContain('aria-label="Melding til alle i Spill 7"');
    expect(html).toMatch(/role="gridcell" aria-colindex="4"><a href="\/m\/2"[^>]*tabindex="-1"/);
    expect(html).toMatch(new RegExp(`data-row="g2"[^]*?fill="${colour("ink")}" text-decoration="underline">Melding`));
    expect(html).toMatch(new RegExp(`data-row="g5"[^]*?fill="${colour("lager")}" text-decoration="underline">Melding`));
    expect(html.match(/tabindex="0"/g)).toHaveLength(2); // the region and Spill 2, Uke 1
  });

  it("tints only the band's row in restordre-fill", () => {
    expect(html.match(/data-tint=""/g)).toHaveLength(1);
    expect(html).toMatch(new RegExp(`data-row="g2"[^>]*data-tint=""[^]*?fill="${colour("restordre-fill")}"`));
  });
});
