import fs from "node:fs";
import path from "node:path";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CostBars } from "./cost-bars";
import { NetGraph, type NetPoint } from "./net-graph";
import { costAxisTop, netDomain, netTicks, spreadLabels } from "./scales";

describe("the Kost per uke axis (founder decision 2026-11-14)", () => {
  it("starts at 40 kr and grows 40 kr at a time to hold the highest Uke", () => {
    expect([34, 40, 41, 62, 121].map(costAxisTop)).toEqual([40, 40, 80, 80, 160]);
    expect(costAxisTop(0)).toBe(40);
    expect(costAxisTop(Number.NaN)).toBe(40);
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
