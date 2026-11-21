/**
 * Chart scales (Story 6.7, UX-DR16, DESIGN.md → Graf over tabell). These are display decisions
 * made from the values the api returned: where an axis ends and which ticks it labels. They never
 * work out a game quantity (AD-10).
 */

/** Netto lager and Posisjon ticks sit on multiples of 20 (DESIGN.md: «ticks in steps of 20»). */
export const NET_STEP = 20;
/** The Kost per uke axis starts at 20 kr and grows 20 kr at a time (founder decision on GitHub
 * issue 126, replacing the 40 kr step of 2026-11-14, so a calm Uke's bars are not thin). */
export const COST_STEP = 20;

/**
 * The top of the Kost per uke axis: the lowest multiple of 20 kr that holds the highest Uke so far,
 * and never below 20 kr. Read from every Uke so far, it can only grow during a game, and no bar is
 * ever cut.
 */
export function costAxisTop(highest: number): number {
  if (!Number.isFinite(highest) || highest <= COST_STEP) return COST_STEP;
  return Math.ceil(highest / COST_STEP) * COST_STEP;
}

/** The lowest top of «Totalkostnad over tid». */
const TOTAL_LOWEST = 50;

/**
 * The top of «Totalkostnad over tid» (Story 6.16, `cost-panel`): the lowest of 50, 100, 200, 500,
 * 1 000, 2 000, … kr that holds the running Total cost, labelled at 0, half and top (`01-landing.png`
 * draws 0 / 25 / 50, `05-spill.png` 0 / 50 / 100). A display choice only.
 */
export function totalAxisTop(highest: number): number {
  if (!Number.isFinite(highest)) return TOTAL_LOWEST;
  for (let decade = 10; ; decade *= 10) {
    for (const step of [1, 2, 5]) {
      const top = decade * step;
      if (top >= TOTAL_LOWEST && top >= highest) return top;
    }
  }
}

/** The y-range of the Netto lager field: multiples of 20 that hold a true zero and every value. */
export function netDomain(values: readonly number[]): [number, number] {
  const finite = values.filter(Number.isFinite);
  const low = Math.floor(Math.min(0, ...finite) / NET_STEP) * NET_STEP;
  let high = Math.ceil(Math.max(0, ...finite) / NET_STEP) * NET_STEP;
  if (high === low) high = low + NET_STEP;
  // `Math.floor(-0)` gives −0; the axis has one zero.
  return [low === 0 ? 0 : low, high === 0 ? 0 : high];
}

/**
 * The labelled ticks of the Netto lager field: multiples of 20 × k inside the domain, with the
 * smallest k that keeps two labels at least 1.4 lines apart, so labels never overlap at any text
 * size. Zero is always one of them.
 */
export function netTicks(domain: readonly [number, number], plotHeight: number, fontSize: number): number[] {
  const [low, high] = domain;
  const perUnit = plotHeight / (high - low);
  let step = NET_STEP;
  while (step * perUnit < 1.4 * fontSize && step < high - low) step += NET_STEP;
  const ticks: number[] = [];
  for (let value = Math.ceil(low / step) * step; value <= high; value += step) ticks.push(value === 0 ? 0 : value);
  return ticks;
}

/**
 * Places direct labels at their wanted y (top of text box at y − size/2) and pushes them apart so
 * no two are closer than `gap`, staying inside [top, bottom]. Labels keep their order by wanted y.
 */
export function spreadLabels(wanted: readonly number[], gap: number, top: number, bottom: number): number[] {
  const order = wanted.map((y, index) => ({ y, index })).sort((a, b) => a.y - b.y);
  const placed = order.map((item) => item.y);
  for (let i = 0; i < placed.length; i++) {
    placed[i] = Math.max(placed[i]!, top, i > 0 ? placed[i - 1]! + gap : -Infinity);
  }
  // Pushed past the bottom: move the stack up as one, then keep the top bound.
  const over = (placed[placed.length - 1] ?? bottom) - bottom;
  if (over > 0) for (let i = 0; i < placed.length; i++) placed[i] = Math.max(top, placed[i]! - over);
  const result = new Array<number>(wanted.length);
  order.forEach((item, i) => {
    result[item.index] = placed[i]!;
  });
  return result;
}
