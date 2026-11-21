import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { OrderBarsTable, type OrderBarsRole } from "../order-bars-table";
import { flowStep, OrderBars } from "./order-bars";
import { colour } from "./palette";

// Story 9.5's Ordrestolper tests, copied verbatim from `origin/epic-9:charts.test.tsx` with the
// component (Story 7.8 reuses it in Spillinnsikt); the merge keeps one copy.
describe("Ordrestolper (Story 9.5)", () => {
  const rows = [
    { orders: [4, 23, 31], own: false, firstLarge: { index: 1, text: "Uke 15" } },
    { orders: [4, 12, 8], own: true, firstLarge: { index: 1, text: "Uke 11" } },
    { orders: [4, 4, null], own: false, firstLarge: null },
  ];
  const html = renderToStaticMarkup(
    <OrderBars width={90} height={150} fontSize={13} xs={[15, 45, 75]} columnWidth={30} rows={rows} chosen={2} title="Ordrestolper" />,
  );

  it("draws a bar per Order, the own Role in ink, the others in order-history", () => {
    expect(html).toContain("<title>Ordrestolper</title>");
    expect(html.match(/data-mark="order"/g)).toHaveLength(8);
    const own = html.split('data-own=""')[1]!.split("</g>")[0]!;
    expect(own).toContain(`fill="${colour("ink")}"`);
    expect(own).not.toContain(`fill="${colour("order-history")}"`);
    expect(html).toContain(`fill="${colour("order-history")}"`);
  });

  it("marks each first large Order with a red dot and its Uke, joined by one diagonal, and the chosen Uke dashed", () => {
    expect(html.match(/data-mark="first-large"/g)).toHaveLength(2);
    expect(html).toContain(">Uke 15</text>");
    expect(html).toMatch(/data-mark="diagonal" points="[\d.]+,[\d.]+ [\d.]+,[\d.]+"/);
    expect(html).toMatch(/data-mark="chosen" x1="75" x2="75"[^>]*stroke-dasharray="3 2"/);
  });

  it("keeps two first large Orders in the same Uke apart", () => {
    const same = rows.map((row) => ({ ...row, firstLarge: { index: 1, text: "Uke 11" } }));
    const twice = renderToStaticMarkup(
      <OrderBars width={90} height={150} fontSize={13} xs={[15, 45, 75]} columnWidth={30} rows={same} chosen={null} title="Ordrestolper" />,
    );
    expect(twice.match(/data-mark="first-large"/g)).toHaveLength(3);
    expect(twice).not.toContain('data-mark="chosen"');
  });

  it("puts every cell on a flow step by its share of the largest Order", () => {
    expect([0, 1, 6, 7, 13, 19, 25, 31].map((order) => flowStep(order, 31))).toEqual([0, 0, 0, 1, 2, 3, 4, 4]);
    expect(flowStep(4, 0)).toBe(0);
  });
});

describe("OrderBarsTable's Forsterkning column (Story 7.8)", () => {
  const texts = {
    week: "Uke",
    weekLabel: (w: number) => `Uke ${w}`,
    amplification: "Forsterkning",
    own: "(deg)",
    none: "–",
    svg: "Ordrestolper",
    axisSvg: "Roller",
    swipe: "Sveip",
  };
  const role = (key: string, extra: Partial<OrderBarsRole> = {}): OrderBarsRole => ({
    key,
    name: key,
    orders: [
      { week: 1, order: 4 },
      { week: 2, order: 12 },
    ],
    firstLargeWeek: 2,
    ...extra,
  });

  it("is left out when no Role gives Forsterkning (Spillinnsikt before Story 9.5)", () => {
    const html = renderToStaticMarkup(<OrderBarsTable label="Ordre" roles={[role("factory"), role("customers")]} texts={texts} />);
    expect(html).not.toContain("Forsterkning");
    expect(html).not.toContain("data-amplification");
    expect(html).toContain('data-role="customers"');
    expect(html).toMatch(/data-flow="4"[^>]*>12</);
  });

  it("stands at the right of each Role's row as soon as a Role gives it", () => {
    const html = renderToStaticMarkup(
      <OrderBarsTable label="Ordre" roles={[role("factory", { amplification: "7.600" }), role("retailer", { amplification: null })]} texts={texts} />,
    );
    expect(html).toContain(">Forsterkning</th>");
    expect(html.match(/data-amplification=""/g)).toHaveLength(2);
    expect(html).toContain("7,6×");
    expect(html).toMatch(/data-amplification=""[^>]*>–</);
  });
});
