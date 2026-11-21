import fs from "node:fs";
import path from "node:path";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChainBand, type SeatBandProps } from "./chain-band";
import { type ChainBandInput, chainLayout } from "./chain-band-layout";
import { flowStep, OrderBars } from "./order-bars";
import { colour } from "./palette";
import { CostArea, endPlaces } from "./cost-area";
import { CostBars } from "./cost-bars";
import { DemandBand, demandAxis } from "./demand-band";
import { NetGraph, type NetPoint } from "./net-graph";
import { NetOverGame, weekLabels } from "./net-over-game";
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
  const band = (extra: Partial<SeatBandProps> = {}) =>
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

describe("Ditt netto lager, hele spillet (Story 9.3)", () => {
  const points = Array.from({ length: 36 }, (_, i) => ({ week: i + 1, net: i < 10 ? 12 : i < 24 ? -30 + i : 8 }));
  const props = {
    width: 300,
    height: 143,
    fontSize: 13,
    points,
    title: "Netto lager",
    formatTick: (value: number) => String(value),
    weekLabel: (week: number) => `Uke ${week}`,
  };

  it("draws the one Seat's line over a true zero, hidden from screen readers with a title", () => {
    const html = renderToStaticMarkup(<NetOverGame {...props} />);
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain("<title>Netto lager</title>");
    expect(html).toContain(`data-weeks="${points.map((p) => p.week).join(" ")}"`);
    expect(html).toContain(">0</text>");
    expect(html).toContain(">-20</text>");
  });

  it("labels the first and last Uke, and every twelfth between with room", () => {
    const x = (week: number) => (week - 1) * 10;
    expect(weekLabels(points, x, 13)).toEqual([1, 12, 24, 36]);
    // Narrow: no room for the twelfths, only the ends.
    expect(weekLabels(points, (week) => (week - 1) * 4, 13)).toEqual([1, 36]);
    expect(weekLabels([{ week: 1, net: 0 }], x, 13)).toEqual([1]);
    expect(weekLabels([], x, 13)).toEqual([]);
  });

  it("draws a game of one Uke as a dot", () => {
    const html = renderToStaticMarkup(<NetOverGame {...props} points={[{ week: 1, net: -4 }]} />);
    expect(html).toContain("<circle");
    expect(html).toContain(">Uke 1</text>");
  });

  it("dashes the shared screen's chosen Uke and shares a scale with the other Roles (Story 9.13)", () => {
    const html = renderToStaticMarkup(<NetOverGame {...props} marker={12} scaleWith={[-75]} />);
    expect(html).toContain('data-mark="marker"');
    expect(html).toContain('stroke-dasharray="3 3"');
    expect(html).toContain(">-80</text>");
    expect(renderToStaticMarkup(<NetOverGame {...props} marker={99} />)).not.toContain('data-mark="marker"');
  });
});

describe("Etterspørselsbånd (Story 9.4)", () => {
  // Classic demand: 4, then 8 from Uke 5; the Seat ordered 24 in Uke 11 once.
  const points = Array.from({ length: 36 }, (_, i) => ({
    week: i + 1,
    x: 10 + i * 20,
    demand: i < 4 ? 4 : 8,
    incoming: i < 4 ? 4 : 7,
    order: i === 10 ? 24 : 6,
  }));
  const props = {
    width: 720,
    height: 195,
    fontSize: 13,
    points,
    columnWidth: 20,
    top: 24,
    demandLabel: "Kundenes etterspørsel: 8",
    largest: { week: 11, text: "Din ordre, 24 i Uke 11" },
    title: "Bånd",
  };

  it("takes an axis of at most four steps that holds every value", () => {
    expect(demandAxis(24)).toEqual({ top: 24, ticks: [0, 8, 16, 24] });
    expect(demandAxis(33)).toEqual({ top: 40, ticks: [0, 10, 20, 30, 40] });
    expect(demandAxis(0)).toEqual({ top: 4, ticks: [0, 4] });
    expect(demandAxis(3)).toEqual({ top: 4, ticks: [0, 4] });
    const big = demandAxis(123_456);
    expect(big.top).toBeGreaterThanOrEqual(123_456);
    expect(big.ticks.length).toBeLessThanOrEqual(5);
  });

  it("draws the band, the line and a bar per Uke, hidden from screen readers with a title", () => {
    const html = renderToStaticMarkup(<DemandBand {...props} />);
    expect(html).toContain('aria-hidden="true"');
    expect(html).toContain("<title>Bånd</title>");
    expect(html).toContain('data-mark="demand"');
    expect(html).toContain('data-mark="incoming"');
    expect(html.match(/data-mark="order"/g)).toHaveLength(36);
    expect(html).toContain('data-week="11" data-x="210"');
    expect(html).toContain(">Kundenes etterspørsel: 8</text>");
    expect(html).toContain(">Din ordre, 24 i Uke 11</text>");
  });

  it("keeps the label of a largest Order at the right edge inside the plot", () => {
    const last = { ...props, largest: { week: 36, text: "Din ordre, 24 i Uke 36" } };
    const html = renderToStaticMarkup(<DemandBand {...last} points={points.map((p) => ({ ...p, order: p.week === 36 ? 24 : 6 }))} />);
    expect(html).toMatch(/data-label="largest"[^>]*text-anchor="end"/);
  });

  it("draws no bar for a zero Order and nothing for no Uker", () => {
    const html = renderToStaticMarkup(<DemandBand {...props} points={[{ ...points[0]!, order: 0 }]} largest={null} />);
    expect(html).not.toContain('data-mark="order"');
    expect(renderToStaticMarkup(<DemandBand {...props} points={[]} largest={null} />)).not.toContain("Kundenes");
  });
});

describe("the four-Role Kjedebånd (Story 9.5)", () => {
  const chain = (width: number, fontSize: number, extra: Partial<ChainBandInput> = {}): ChainBandInput => ({
    width,
    fontSize,
    upstream: "Produksjon",
    downstream: "Kundene",
    maxUnits: 40,
    nodes: [
      { label: "Fabrikk", numbers: ["Restordre 3"], inventory: 0, backlog: 3, own: false },
      { label: "Distributør", numbers: ["Restordre 34"], inventory: 0, backlog: 34, own: false },
      { label: "Grossist", numbers: ["Restordre 19"], inventory: 0, backlog: 19, own: true },
      { label: "Detaljist", numbers: ["Lager 12"], inventory: 12, backlog: 0, own: false },
    ],
    orders: ["22", "12", "12", "8", "8"],
    supplyLines: ["50", "52", null, "13"],
    ...extra,
  });
  const overlap = (a: { x: number; y: number; width: number }, b: { x: number; y: number; width: number }) =>
    Math.abs(a.y - b.y) < 1 && a.x < b.x + b.width && b.x < a.x + a.width;

  it("draws the chain from Produksjon to Kundene with the own node in a 1.4 px ink border", () => {
    const html = renderToStaticMarkup(<ChainBand variant="chain" title="Hele kjeden" {...chain(1000, 13)} />);
    expect(html).toMatch(/^<svg [^>]*data-chart="band" data-variant="chain"/);
    expect(html).toContain("<title>Hele kjeden</title>");
    expect(html.match(/data-mark="node"/g)).toHaveLength(4);
    expect(html).toMatch(/data-mark="node" data-own=""><rect [^>]*stroke="#[0-9A-F]+" stroke-width="1.4"/);
    expect(html.match(/data-mark="backlog"/g)).toHaveLength(3);
    expect(html.match(/data-mark="stock"/g)).toHaveLength(1);
    // A box on the goods line for each Role with goods on the way, none where there are none.
    expect(html.match(/data-mark="arrival"/g)).toHaveLength(3);
    const layout = chainLayout(chain(1000, 13));
    const texts = layout.labels.map((label) => label.text);
    expect(texts[0]).toBe("Produksjon");
    expect(texts).toContain("Kundene");
    expect(layout.labels.find((l) => l.text === "Produksjon")!.x).toBe(0);
    // Upstream at the left: Fabrikk's node left of Detaljist's.
    expect(layout.nodes[0]!.box.x).toBeLessThan(layout.nodes[3]!.box.x);
  });

  it.each([
    [320, 13],
    [360, 13],
    [320, 26],
    [1000, 13],
  ])("keeps every label inside %i px at %i px text, with no two overlapping", (width, fontSize) => {
    const layout = chainLayout(chain(width, fontSize));
    for (const label of layout.labels) {
      expect(label.x).toBeGreaterThanOrEqual(0);
      expect(label.x + label.width).toBeLessThanOrEqual(width + 0.01);
    }
    for (const [i, a] of layout.labels.entries()) {
      for (const b of layout.labels.slice(i + 1)) expect(overlap(a, b), `${a.text} / ${b.text}`).toBe(false);
    }
  });

  it("sets the node labels on two rows when they would meet, and keeps one bar scale and height", () => {
    expect(chainLayout(chain(1000, 13)).staggered).toBe(false);
    expect(chainLayout(chain(320, 26)).staggered).toBe(true);
    const small = chainLayout(chain(360, 13, { nodes: chain(360, 13).nodes.map((n) => ({ ...n, inventory: 0, backlog: 1 })) }));
    const large = chainLayout(chain(360, 13));
    expect(small.height).toBe(large.height);
    expect(small.stockUnit).toBe(large.stockUnit);
    // The tallest bar of the game is at most 44 px.
    expect(large.stockUnit * 40).toBeLessThanOrEqual(44);
  });
});

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
