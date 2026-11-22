import { expect, type Page } from "@playwright/test";

/** The Graf over tabell checks of Story 6.7, shared by the play screen's and the Landing's tests
 * (Story 6.8): marks over their columns, labels apart, text readable. */

/** Every drawn Week mark's distance in px from the centre of its `th[scope=col]`, the now-line's
 * from the nå column's right edge, and the Uker drawn. */
export function alignment(page: Page) {
  return page.evaluate(() => {
    const shown = (el: Element) => el.getClientRects().length > 0;
    const centres = new Map<number, number>();
    let nowRight = Number.NaN;
    for (const th of document.querySelectorAll<HTMLElement>("th[scope=col][data-col]")) {
      if (!shown(th)) continue;
      const r = th.getBoundingClientRect();
      centres.set(Number(th.dataset.col), r.left + r.width / 2);
      if (th.hasAttribute("data-now")) nowRight = r.right;
    }
    const off: { mark: string; week: number; by: number }[] = [];
    const drawn = new Set<number>();
    const at = (mark: string, week: number, x: number) => {
      drawn.add(week);
      const centre = centres.get(week);
      off.push({ mark, week, by: centre === undefined ? Number.POSITIVE_INFINITY : Math.abs(x - centre) });
    };
    for (const svg of document.querySelectorAll<SVGSVGElement>("svg[data-chart=net], svg[data-chart=cost]")) {
      if (!shown(svg)) continue;
      const left = svg.getBoundingClientRect().left;
      for (const el of svg.querySelectorAll<SVGElement>("[data-mark]")) {
        const mark = el.dataset.mark!;
        if (el.dataset.weeks) {
          const xs = el.dataset.x!.split(" ").map(Number);
          el.dataset.weeks.split(" ").forEach((week, i) => at(mark, Number(week), left + xs[i]!));
        } else if (mark === "cost") {
          for (const rect of el.querySelectorAll("rect")) {
            const r = rect.getBoundingClientRect();
            at(mark, Number(el.dataset.week), r.left + r.width / 2);
          }
        } else {
          const r = el.getBoundingClientRect();
          at(mark, Number(el.dataset.week), r.left + r.width / 2);
        }
      }
    }
    const line = document.querySelector<HTMLElement>("[data-now-line]")!.getBoundingClientRect();
    return {
      worst: Math.max(...off.map((o) => o.by)),
      off: off.filter((o) => o.by > 1),
      marks: off.length,
      drawn: [...drawn].sort((a, b) => a - b),
      nowLine: Math.abs(line.left + line.width / 2 - nowRight),
    };
  });
}

/** Pairs of graph labels (SVG text: axis ticks, «Nå», the direct labels) whose boxes overlap,
 * and labels that leave their SVG. */
export function labelProblems(page: Page) {
  return page.evaluate(() => {
    // The Matrisevegg has its own rules (9 px cells, the fit rule): `landing.spec.ts`, `overview.spec.ts`.
    const texts = [...document.querySelectorAll<SVGTextElement>('svg[data-chart]:not([data-chart="matrix-wall"]) text')].filter(
      (t) => t.getClientRects().length > 0,
    );
    const boxes = texts.map((t) => ({ text: t.textContent, box: t.getBoundingClientRect(), svg: t.ownerSVGElement!.getBoundingClientRect() }));
    const problems: string[] = [];
    boxes.forEach((a, i) => {
      if (a.box.left < a.svg.left - 0.5 || a.box.right > a.svg.right + 0.5 || a.box.top < a.svg.top - 0.5 || a.box.bottom > a.svg.bottom + 0.5) {
        problems.push(`${a.text} leaves its chart`);
      }
      boxes.slice(i + 1).forEach((b) => {
        const w = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
        const h = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
        if (w > 0.5 && h > 0.5) problems.push(`${a.text} overlaps ${b.text}`);
      });
    });
    return problems;
  });
}

/** The direct labels of the visible Netto lager graph that the Replay's projection runs through
 * (Story 10.6): its dashed line, sampled every px, or its end dot inside a label's text box. */
export function projectionCrossings(page: Page) {
  return page.evaluate(() => {
    const svg = [...document.querySelectorAll<SVGSVGElement>('svg[data-chart="net"]')].find((s) => s.getClientRects().length > 0);
    const mark = svg?.querySelector<SVGGElement>("[data-mark=projection]");
    if (!svg || !mark) return ["no projection"];
    const path = mark.querySelector("path")!;
    const matrix = path.getScreenCTM()!;
    const points: { x: number; y: number }[] = [];
    for (let at = 0; at <= path.getTotalLength(); at += 1) {
      const p = path.getPointAtLength(at).matrixTransform(matrix);
      points.push({ x: p.x, y: p.y });
    }
    const dot = mark.querySelector("circle")?.getBoundingClientRect();
    const problems: string[] = [];
    for (const label of svg.querySelectorAll<SVGTextElement>("text[data-label=net], text[data-label=position]")) {
      const box = label.getBoundingClientRect();
      const inside = (x: number, y: number) => x > box.left + 0.5 && x < box.right - 0.5 && y > box.top + 0.5 && y < box.bottom - 0.5;
      if (points.some((p) => inside(p.x, p.y))) problems.push(`the line crosses ${label.textContent}`);
      if (dot && Math.min(dot.right, box.right) > Math.max(dot.left, box.left) && Math.min(dot.bottom, box.bottom) > Math.max(dot.top, box.top)) {
        problems.push(`the dot meets ${label.textContent}`);
      }
    }
    return problems;
  });
}

/** How many lines the projection sentence's sum takes (Story 10.6): the text from after «: » to
 * before « hvis», measured by its line boxes. */
export function projectionSumLines(page: Page) {
  return page.evaluate(() => {
    const sentence = document.querySelector<HTMLElement>("[data-projection-sentence]")!;
    const node = [...sentence.childNodes].find((n) => n.nodeType === 3 && n.textContent!.includes(": "))!;
    const text = node.textContent!;
    const range = document.createRange();
    range.setStart(node, text.indexOf(": ") + 2);
    range.setEnd(node, text.indexOf(" hvis"));
    return new Set([...range.getClientRects()].filter((r) => r.width > 0).map((r) => Math.round(r.top))).size;
  });
}

/** No text in the page below 13 px (SVG text included) and no table cell whose text is cut off.
 * The Matrisevegg's cells are the one place allowed 9 px (DESIGN.md → Typography → Floors). */
export async function textReadable(page: Page) {
  const found = await page.evaluate(() => {
    const small = [...document.querySelectorAll<Element>("main *")]
      .filter((el) => el.getClientRects().length > 0 && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent?.trim()))
      .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 13)
      .filter((el) => !el.closest('svg[data-chart="matrix-wall"]'))
      .map((el) => el.textContent?.trim());
    const clipped = [...document.querySelectorAll<HTMLElement>("main th, main td")]
      .filter((el) => el.getClientRects().length > 0 && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1))
      .map((el) => el.textContent?.trim());
    return { small, clipped };
  });
  expect(found).toEqual({ small: [], clipped: [] });
}
