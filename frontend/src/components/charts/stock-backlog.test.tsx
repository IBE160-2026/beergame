import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { colour } from "./palette";
import { StockBacklog, stockBands } from "./stock-backlog";

describe("Lager og restordre (Story 7.8)", () => {
  const rows = [
    { stock: [12, 0, 4], backlog: [0, 6, 0] },
    { stock: [8, 2, null], backlog: [0, 0, null] },
  ];

  it("splits each band at the game's largest stock against its largest backlog, one scale for all", () => {
    const [first, second] = stockBands(200, rows);
    // 100 px a band, 94 px inside its gaps: 12 stock + 6 backlog → 2/3 above the zero line.
    expect(first!.unit).toBeCloseTo(94 / 18);
    expect(first!.zero).toBe(Math.round(3 + 12 * (94 / 18)));
    expect(second!.zero).toBe(Math.round(103 + 12 * (94 / 18)));
    expect(first!.unit).toBe(second!.unit);
  });

  it("puts the zero line at the band's foot when nothing was ever held back", () => {
    const [band] = stockBands(100, [{ stock: [5, 3], backlog: [0, 0] }]);
    expect(band!.zero).toBe(97);
  });

  it("draws stock up in lager and backlog down in restordre, none for zero or no Uke", () => {
    const html = renderToStaticMarkup(<StockBacklog width={90} height={200} xs={[15, 45, 75]} columnWidth={30} rows={rows} title="Lager og restordre" />);
    expect(html).toContain("<title>Lager og restordre</title>");
    expect(html.match(/data-mark="stock"/g)).toHaveLength(4);
    expect(html.match(/data-mark="backlog"/g)).toHaveLength(1);
    expect(html).toContain(`fill="${colour("lager")}"`);
    expect(html).toContain(`fill="${colour("restordre")}"`);
    const [band] = stockBands(200, rows);
    // The largest stock reaches the band's top gap (within the zero line's whole-px rounding); the backlog bar starts under the zero line.
    expect(html).toMatch(new RegExp(`data-mark="stock" x="[\\d.]+" y="3(\\.\\d+)?" width="21" height="${Math.round(12 * band!.unit * 100) / 100}"`));
    expect(html).toMatch(new RegExp(`data-mark="backlog" x="[\\d.]+" y="${band!.zero + 1}"`));
  });
});
