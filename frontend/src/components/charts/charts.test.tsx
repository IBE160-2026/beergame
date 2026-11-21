import fs from "node:fs";
import path from "node:path";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChainBand } from "./chain-band";
import { CostArea, endPlaces } from "./cost-area";
import { CostBars } from "./cost-bars";
import { textWidth } from "./chain-band-layout";
import { CostDistribution, distributionAxis } from "./cost-distribution";
import { NetGraph, type NetPoint } from "./net-graph";
import { costAxisTop, netDomain, netTicks, spreadLabels, totalAxisTop } from "./scales";

describe("the Kost per uke axis (Issue #126)", () => {
  it("starts at 20 kr and grows 20 kr at a time to hold the highest Uke", () => {
    expect([6, 20, 21, 34, 41, 62, 121].map(costAxisTop)).toEqual([20, 20, 40, 40, 60, 80, 140]);
    expect(costAxisTop(0)).toBe(20);
    expect(costAxisTop(Number.NaN)).toBe(20);
  });
});

describe("the Totalkostnad over tid axis (Story 6.16)", () => {
  it("is the lowest of 50, 100, 200, 500, 1 000 … kr that holds the running total", () => {
    expect([0, 24, 50, 68, 101, 220, 380, 501, 1954, 2001, 2266, 2501].map(totalAxisTop)).toEqual([50, 50, 50, 100, 200, 250, 500, 1000, 2000, 2500, 2500, 5000]);
    expect(totalAxisTop(Number.NaN)).toBe(50);
  });
});

describe("the Netto lager range and ticks", () => {
  it("holds a true zero and every value on multiples of 20", () => {
    expect(netDomain([12, -13, 3])).toEqual([-20, 20]);
    expect(netDomain([24, 30])).toEqual([0, 40]);
    expect(netDomain([-56, 46])).toEqual([-60, 60]);
    expect(netDomain([0, 0])).toEqual([0, 20]);
    expect(netDomain([])).toEqual([0, 20]);
  });

  it("labels every 20 while there is room, else multiples of 40, 60 …, always with 0", () => {
    expect(netTicks([-40, 20], 120, 13)).toEqual([-40, -20, 0, 20]);
    // 120 units over 60 px: 20 units are 10 px, under 1.4 lines, so every 40.
    expect(netTicks([-60, 60], 60, 13)).toEqual([-40, 0, 40]);
    // Larger text in a field too short for it: labels thin out further, 0 stays.
    expect(netTicks([-60, 60], 120, 26)).toEqual([-40, 0, 40]);
    expect(netTicks([-60, 60], 60, 26)).toEqual([0]);
  });
});

describe("direct labels", () => {
  it("are pushed apart and kept inside the field", () => {
    expect(spreadLabels([50, 52], 16, 0, 200)).toEqual([50, 66]);
    expect(spreadLabels([52, 50], 16, 0, 200)).toEqual([66, 50]);
    expect(spreadLabels([195, 196], 16, 0, 200)).toEqual([184, 200]);
    expect(spreadLabels([2, 3], 16, 10, 200)).toEqual([10, 26]);
  });
});

const POINTS: NetPoint[] = [
  { week: 9, x: 10, net: -8, position: 4 },
  { week: 10, x: 31, net: -14, position: -2 },
  { week: 11, x: 52, net: -20, position: -4 },
];

function net(extra: Partial<Parameters<typeof NetGraph>[0]> = {}) {
  return renderToStaticMarkup(
    <NetGraph
      width={180}
      height={100}
      fontSize={13}
      points={POINTS}
      nowX={62}
      title="Graf over Netto lager"
      netLabel="Restordre 20"
      positionLabel="Posisjon −4"
      nowLabel="Nå"
      {...extra}
    />,
  );
}

describe("NetGraph", () => {
  it("renders on the server, with a <title>, the marks at the given x and the labels", () => {
    const html = net();
    expect(html).toMatch(/^<svg [^>]*width="180" height="100"/);
    expect(html).toContain("<title>Graf over Netto lager</title>");
    expect(html).toContain('data-weeks="9 10 11" data-x="10 31 52"');
    expect(html.match(/data-mark="position"/g)).toHaveLength(3);
    expect(html).toContain('data-mark="position" data-week="11" x="50"');
    expect(html).toContain(">Restordre 20</text>");
    expect(html).toContain(">Posisjon −4</text>");
    expect(html).toContain(">Nå</text>");
  });

  it("draws no projection in the Klassespill, and one only when asked (Epic 10)", () => {
    expect(net()).not.toContain("projection");
    expect(net({ projection: [{ x: 52, value: -20 }, { x: 94, value: -5 }] })).toContain('data-mark="projection"');
  });

  it("at mini scale (Spillkort, Story 6.17) draws the Netto lager line, its dot and «Nå» only", () => {
    const html = net({ mini: true });
    expect(html).toContain('data-mark="net"');
    expect(html).toContain('data-mark="now"');
    expect(html).toContain(">Nå</text>");
    expect(html).not.toContain('data-mark="position"');
    expect(html).not.toContain("data-label=\"net\"");
    expect(html).not.toContain("data-label=\"position\"");
    // No Posisjon path: only the two fills and the line's two halves (above and below zero).
    expect(html.match(/<path /g)).toHaveLength(4);
  });

  it("paints from the theme tokens, never with classes or CSS variables", () => {
    const html = net();
    expect(html).not.toMatch(/class=|var\(--/);
    expect(html).toContain('stroke="#B5423A"'); // restordre below zero
  });
});

describe("CostBars", () => {
  it("stacks holding cost below backlog cost, 1.5 px apart, and cuts no bar", () => {
    const html = renderToStaticMarkup(
      <CostBars
        width={100}
        height={50}
        fontSize={13}
        top={80}
        nowX={60}
        barWidth={10}
        title="Kost per uke"
        bars={[
          { week: 1, x: 10, holding: 6, backorder: 0 },
          { week: 2, x: 30, holding: 2, backorder: 4 },
          { week: 3, x: 50, holding: 0, backorder: 56 },
        ]}
      />,
    );
    expect(html).toContain("<title>Kost per uke</title>");
    expect(html.match(/data-mark="cost"/g)).toHaveLength(3);
    // y = 49 − value × 41 / 80 (range 49 … 10 for 0 … 80 kr, at 13 px).
    const y = (kr: number) => 49 - (kr * (49 - 10)) / 80;
    const rects = (week: number) =>
      [...html.split(`data-week="${week}"`)[1]!.split("</g>")[0]!.matchAll(/<rect x="[\d.]+" y="([\d.-]+)" width="10" height="([\d.-]+)" fill="(#[0-9A-F]+)"/g)].map(
        (m) => ({ top: Number(m[1]), bottom: Number(m[1]) + Number(m[2]), fill: m[3] }),
      );
    const [holding, backorder] = rects(2);
    expect(holding).toMatchObject({ fill: "#2B6CA3", bottom: y(0) }); // lager at the bottom
    expect(backorder!.fill).toBe("#B5423A"); // restordre on top
    expect(holding!.top - backorder!.bottom).toBeCloseTo(1.5); // 1.5 px apart
    expect(backorder!.top).toBeCloseTo(y(6)); // the top stays at the Uke's value
    // The costliest Uke reaches its value under the axis top, never above the chart.
    const [only] = rects(3);
    expect(only!.top).toBeCloseTo(y(56));
    expect(only!.top).toBeGreaterThanOrEqual(y(80));
  });
});

describe("ChainBand", () => {
  const band = (extra: Partial<Parameters<typeof ChainBand>[0]> = {}) =>
    renderToStaticMarkup(
      <ChainBand
        width={358}
        fontSize={13}
        inventory={0}
        backlog={13}
        slots={[4, 4, 8]}
        overdue={0}
        title="Kjedebånd"
        labels={LABELS}
        {...extra}
      />,
    );

  it("renders on the server with a <title>, the node, a red bar below and a box per known arrival", () => {
    const html = band();
    expect(html).toMatch(/^<svg [^>]*width="358"[^>]*data-chart="band" data-variant="seat"/);
    expect(html).toContain("<title>Kjedebånd</title>");
    expect(html.match(/data-mark="arrival"/g)).toHaveLength(3);
    expect(html).toMatch(/data-mark="backlog"[^>]*fill="#B5423A"/);
    expect(html).not.toContain('data-mark="stock"');
    expect(html).not.toContain('data-mark="overdue"');
    for (const text of ["Distributør", "Detaljist", "Din ordre", "Ordre inn 8", "Levering 4", "Sendt 4", "Restordre 13", "På vei 16"]) {
      expect(html).toContain(`>${text}</text>`);
    }
  });

  it("draws stock as a blue bar and overdue units as a dashed box with their number", () => {
    const html = band({ inventory: 12, backlog: 0, overdue: 7, labels: { ...LABELS, stock: ["Lager 12"], overdue: "7" } });
    expect(html).toMatch(/data-mark="stock"[^>]*fill="#2B6CA3"/);
    expect(html).toMatch(/data-mark="overdue"><rect [^>]*stroke-dasharray="3 2"/);
    expect(html).toContain('data-label="overdue"');
  });

  it("paints from the theme tokens, never with classes or CSS variables", () => {
    expect(band()).not.toMatch(/class=|var\(--/);
  });
});

const LABELS = {
  upstream: "Distributør",
  downstream: "Detaljist",
  order: "Din ordre",
  incoming: "Ordre inn 8",
  delivery: "Levering 4",
  shipped: "Sendt 4",
  stock: ["Restordre 13"],
  supplyLine: "På vei 16",
  overdue: null,
};

describe("the chart module (AD-18)", () => {
  it("is the only code that imports a chart library", () => {
    const src = path.resolve(__dirname, "..", "..");
    const charts = path.resolve(__dirname);
    const found: string[] = [];
    const walk = (dir: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (/\.[cm]?[jt]sx?$/.test(entry.name) && !full.startsWith(charts)) {
          if (/from\s+["'](?:d3(?:-[a-z]+)?|recharts|chart\.js|victory|@nivo\/[a-z-]+|visx|@visx\/[a-z-]+)["']/.test(fs.readFileSync(full, "utf8"))) {
            found.push(path.relative(src, full));
          }
        }
      }
    };
    walk(src);
    expect(found).toEqual([]);
  });
});

describe("Totalkostnad over tid (Story 6.16)", () => {
  const props = { width: 240, height: 117, fontSize: 13, title: "t", formatTick: String, firstLabel: "Uke 1", lastLabel: "Uke 4" };

  it("stacks holding under backlog on a true zero, hidden from screen readers", () => {
    const html = renderToStaticMarkup(
      <CostArea
        {...props}
        points={[
          { week: 1, holding: 6, backorder: 0 },
          { week: 2, holding: 6, backorder: 4 },
        ]}
      />,
    );
    expect(html).toMatch(/<svg[^>]*aria-hidden="true"/);
    expect(html).toContain("<title>t</title>");
    expect(html).toContain('data-mark="holding-area"');
    expect(html).toContain('data-mark="backorder-area"');
    expect(html).toContain(">0</text>");
    expect(html).toContain(">50</text>");
    expect(html).toContain(">Uke 4</text>");
  });

  it("draws a lone Uke as a short block, with no backlog area while none is owed", () => {
    const html = renderToStaticMarkup(<CostArea {...props} points={[{ week: 1, holding: 6, backorder: 0 }]} />);
    expect(html).toMatch(/data-mark="holding-area"/);
    expect(html).not.toContain("backorder-area");
    expect(html).not.toContain(">Uke 4</text>");
  });
});

describe("Kjedens kostnad over tid's end labels (Story 6.18)", () => {
  const props = { width: 240, height: 117, fontSize: 13, title: "t", formatTick: String, firstLabel: "Uke 1", lastLabel: "Uke 4" };

  it("labels the final values at the right end, and none without endLabels", () => {
    const points = [
      { week: 1, holding: 6, backorder: 0 },
      { week: 2, holding: 10, backorder: 30 },
    ];
    const html = renderToStaticMarkup(
      <CostArea {...props} points={points} endLabels={{ holding: "Lager 10,00", backorder: "Restordre 30,00" }} />,
    );
    expect(html).toContain('data-mark="end-labels"');
    expect(html).toContain(">Lager 10,00</text>");
    expect(html).toContain(">Restordre 30,00</text>");
    expect(renderToStaticMarkup(<CostArea {...props} points={points} />)).not.toContain("end-labels");
  });

  it("keeps the two labels a line apart and inside the plot, holding below", () => {
    const y = (value: number) => 100 - value; // base 100, top 0
    for (const last of [
      { week: 9, holding: 0, backorder: 0 },
      { week: 9, holding: 99, backorder: 1 },
      { week: 9, holding: 1, backorder: 99 },
      { week: 9, holding: 50, backorder: 50 },
    ]) {
      const { holding, backorder } = endPlaces(last, y, 0, 100, 13);
      expect(holding - backorder).toBeGreaterThanOrEqual(13 * 1.2 - 1e-9);
      expect(backorder).toBeGreaterThanOrEqual(13 * 0.6);
      expect(holding).toBeLessThanOrEqual(100 - 13 * 0.6);
    }
  });
});

describe("Kostnadsfordeling (Story 7.6)", () => {
  const props = {
    fontSize: 13,
    values: [660, 1954, 1500, 2600, 3532],
    median: 1954,
    lower: 1500,
    upper: 2600,
    medianLabel: "Median 1 954",
    title: "Kjedekost i hvert ferdige spill, 5 spill",
    formatTick: (value: number) => value.toLocaleString("nb-NO"),
  };

  it("runs its axis from 0 in 1–2–2,5–5 steps whose labels have room", () => {
    const label = () => 40; // 1.6 labels: 64 px between ticks at least
    expect(distributionAxis(3532, 400, label)).toEqual([0, 1000, 2000, 3000, 4000]);
    expect(distributionAxis(3532, 120, label)).toEqual([0, 5000]);
    expect(distributionAxis(800, 400, label)).toEqual([0, 200, 400, 600, 800]);
    expect(distributionAxis(0, 400, label)).toEqual([0, 1]);
    // Narrower than two labels: no step fits, so 0 and the lowest top that holds the values.
    expect(distributionAxis(3532, 20, label)).toEqual([0, 5000]);
    expect(distributionAxis(3532, 0, label)).toEqual([0, 5000]);
  });

  it("draws one tick per game, the middle-half box, the labelled median and a title, all inside", () => {
    for (const width of [288, 352]) {
      const html = renderToStaticMarkup(<CostDistribution {...props} width={width} />);
      expect(html.match(/data-mark="game"/g)).toHaveLength(5);
      expect(html).toContain('data-mark="box"');
      expect(html).toContain('data-mark="median"');
      expect(html).toContain(">Median 1 954</text>");
      expect(html).toContain("<title>Kjedekost i hvert ferdige spill, 5 spill</title>");
      expect(html).toContain('aria-hidden="true"');
      // Every label inside the drawing, by the same upper-bound width the layout uses.
      for (const [, x, weight, text] of html.matchAll(/<text x="([\d.]+)"[^>]*?(?:font-weight="(\d+)")?[^>]*>([^<]+)<\/text>/g)) {
        expect(Number(x)).toBeGreaterThanOrEqual(0);
        expect(Number(x) + textWidth(text!, 13, weight === "600" ? 600 : 400)).toBeLessThanOrEqual(width + 0.5);
      }
    }
  });
});
