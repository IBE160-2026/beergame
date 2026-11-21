import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { type GraphColumn, type GraphField, GraphOverTable } from "./graph-over-table";

const COLUMNS: GraphColumn[] = [
  { week: 1, when: "past", phone: false },
  { week: 2, when: "past", phone: true },
  { week: 3, when: "now", phone: true },
  { week: 4, when: "future", phone: true },
];

const seen: { width: number; xs: readonly number[]; nowX: number; columns: number }[] = [];
const FIELD: GraphField = {
  key: "f",
  caption: "Felt",
  heightEm: 4,
  render: (size) => {
    seen.push({ width: size.width, xs: size.xs, nowX: size.nowX, columns: size.columns.length });
    return { plot: <svg data-chart="f" width={size.width} height={size.height} />, axis: <svg data-chart="axis" /> };
  },
};

function render(fixed?: { labelWidth: number; columnWidth: number; fontSize: number }) {
  seen.length = 0;
  return renderToStaticMarkup(
    <GraphOverTable
      label="Graf og tabell"
      columns={COLUMNS}
      fields={[FIELD]}
      fixed={fixed}
      head={
        <tr>
          <th scope="row">Uke</th>
        </tr>
      }
      body={null}
    />,
  );
}

describe("GraphOverTable", () => {
  it("is one named, focusable region whose graph rows are hidden from screen readers", () => {
    const html = render();
    expect(html).toContain('role="region" aria-label="Graf og tabell" tabindex="0"');
    expect(html).toMatch(/<tr aria-hidden="true" data-field="f" data-variant="phone" class="lg:hidden">/);
    expect(html).toMatch(/<tr aria-hidden="true" data-field="f" data-variant="laptop" class="hidden lg:table-row">/);
    // The caption is read; it spans the label column and the variant's columns.
    expect(html).toContain('<td colSpan="4"');
    expect(html).toContain('<td colSpan="5"');
  });

  it("draws nothing in the browser until it has measured the columns", () => {
    expect(render()).not.toContain('data-chart="f"');
    expect(seen).toEqual([]);
  });

  it("with a fixed layout draws each variant over its own columns, with the now-line", () => {
    const html = render({ labelWidth: 80, columnWidth: 20, fontSize: 13 });
    expect(seen).toEqual([
      { width: 60, xs: [10, 30, 50], nowX: 40, columns: 3 },
      { width: 80, xs: [10, 30, 50, 70], nowX: 60, columns: 4 },
    ]);
    expect(html).toMatch(/data-now-line=""[^>]*style="left:119.3px"/);
  });

  it("without a nå column (a finished game) draws no now-line and puts nowX past the last column", () => {
    seen.length = 0;
    const html = renderToStaticMarkup(
      <GraphOverTable
        label="Graf og tabell"
        columns={COLUMNS.map((column) => ({ ...column, when: "past" as const }))}
        fields={[FIELD]}
        fixed={{ labelWidth: 80, columnWidth: 20, fontSize: 13 }}
        head={null}
        body={null}
      />,
    );
    expect(seen.map((size) => size.nowX)).toEqual([60, 80]);
    expect(html).not.toContain("data-now-line");
  });
});
