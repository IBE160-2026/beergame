import { scaleLinear } from "d3-scale";

/**
 * The Kjedebånd's layout (Story 6.9, UX-DR14, UX-DR15, DESIGN.md → Kjedebånd): where the node,
 * the bars, the boxes on the pipe and every label go in a band of a given width and text size.
 * A pure function of the numbers it is given; the only arithmetic is the pixel scale (AD-10).
 *
 * Geometry, left to right: the upstream end, the pipe with its boxes (the overdue box apart at
 * the far end, then the known arrivals, the soonest next to the node), the node, then the goods line out to the downstream end.
 * The order line runs along the top, right to left. Labels sit in three rows (over the order
 * line, over the goods line, under it); one whose spot is taken or too narrow wraps into rows
 * under the band, so no two labels ever overlap.
 */

/** DESIGN.md `chain-pipe-unit-phone` and `chain-stock-unit-phone`: the maxima, in px per unit. */
export const PIPE_UNIT = 1.4;
export const STOCK_UNIT = 0.82;
/** The pipe a band must hold at one scale: the worst Uke DESIGN.md names («På vei 56 + 13»)
 * with room to spare, so a game keeps one scale at a given width. A Uke that needs more shrinks
 * that Uke only. */
export const WORST_PIPE_UNITS = 80;

const NODE_W = 40;
const BOX_H = 12;
const BOX_GAP = 3;
/** The fixed width of the overdue box (units with no known date: not to scale). */
const OVERDUE_W = 24;
/** Room for the arrowhead between the last box and the node. */
const HEAD = 8;
const PAD = 2;
/** Source Sans 3's box above and below the baseline, in em (ascender 1024, descender 400). */
const ASCENT = 1.03;
const DESCENT = 0.41;
/** The gap kept between two labels in a row, in em. */
const LABEL_GAP = 0.4;

export type BandLabels = {
  /** The end labels: the upstream neighbour (or «Produksjon»), the downstream (or «Kundene»). */
  upstream: string;
  downstream: string;
  /** «Din ordre», along the order line going out (no number until one is typed, Story 6.11). */
  order: string;
  /** «Ordre inn 8», along the order line coming in. */
  incoming: string;
  /** «Levering 4» into the node, «Sendt 4» out of it. */
  delivery: string;
  shipped: string;
  /** «Lager 12», «Restordre 13», or both when both are held (capacity, Story 6.22). */
  stock: readonly string[];
  /** «På vei 16», under the pipe. */
  supplyLine: string;
  /** The overdue units' number, written above their box; null when there are none. */
  overdue: string | null;
};

export type BandInput = {
  width: number;
  fontSize: number;
  inventory: number;
  backlog: number;
  /** The known arrivals' quantities, soonest first (`supply_line_slots`). */
  slots: readonly number[];
  overdue: number;
  /** A typed Order not yet confirmed (Story 6.11): one more box, last on the pipe. */
  typed?: number;
  labels: BandLabels;
};

export type Box = { x: number; y: number; width: number; height: number };

export type LabelKey =
  | "upstream"
  | "downstream"
  | "order"
  | "incoming"
  | "delivery"
  | "shipped"
  | "stock"
  | "supplyLine"
  | "overdue";

export type PlacedLabel = {
  key: LabelKey;
  text: string;
  /** The left edge of the text box and the baseline. */
  x: number;
  y: number;
  /** The estimated width (`textWidth`), which the real text never exceeds. */
  width: number;
  weight: 400 | 600 | 700;
  muted: boolean;
  /** Moved into the rows under the band because its own spot had no room. */
  wrapped: boolean;
};

export type BandLayout = {
  width: number;
  height: number;
  fontSize: number;
  /** The common factor (≤ 1) on both maxima, and the units it gives. */
  scale: number;
  pipeUnit: number;
  stockUnit: number;
  node: Box;
  /** The order line's y (the node's top) and the goods line's (the node's baseline). */
  orderY: number;
  goodsY: number;
  stockBar: Box | null;
  backlogBar: Box | null;
  boxes: Box[];
  /** The typed Order's box, after the known arrivals; null when none is typed or it is 0. */
  typedBox: Box | null;
  overdueBox: Box | null;
  labels: PlacedLabel[];
};

/** Character widths of Source Sans 3 in em, rounded up, for a conservative text width. */
const NARROW = /[ijlrtfI.,:;'’!|() ]/;
const WIDE = /[mwMWæÆ]/;
const UPPER = /[A-ZÆØÅ]/;

/** An upper bound on a label's width in px at `fontSize` (the real face is narrower; Playwright
 * checks this bound against the rendered text). */
export function textWidth(text: string, fontSize: number, weight: 400 | 600 | 700 = 400): number {
  let em = 0;
  for (const char of text) {
    if (NARROW.test(char)) em += 0.32;
    else if (WIDE.test(char)) em += 0.82;
    else if (UPPER.test(char)) em += 0.64;
    else em += 0.54; // lower case, digits, «−»
  }
  const bold = weight === 400 ? 1 : weight === 600 ? 1.04 : 1.07;
  return Math.ceil(em * fontSize * bold);
}

type Wanted = {
  key: LabelKey;
  text: string;
  weight: 400 | 600 | 700;
  muted?: boolean;
  row: 0 | 1 | 2;
  /** Where the text is anchored and to which side it runs. */
  at: number;
  anchor: "start" | "end" | "middle";
  /** The room it must stay in. */
  min: number;
  max: number;
};

export function bandLayout(input: BandInput): BandLayout {
  const { width, fontSize: f, inventory, backlog, slots, overdue, typed = 0, labels } = input;
  // The node in the middle: the left half holds the pipe, the right the way out.
  const nodeX = Math.round(width / 2 - NODE_W / 2);
  const nodeRight = nodeX + NODE_W;
  const overdueRoom = overdue > 0 ? OVERDUE_W + BOX_GAP : 0;
  // The typed Order is drawn as the last box, at the same scale as the known ones.
  const shown = [...slots, typed].filter((quantity) => quantity > 0);
  const gaps = Math.max(0, shown.length - 1) * BOX_GAP;
  // The pipe's room: from the left end to the arrowhead at the node.
  const room = Math.max(0, nodeX - HEAD - PAD);
  // One factor for pipe and stock, from the width: the worst Uke's pipe fits. A Uke that needs
  // more (an unusual game) is drawn smaller still, never past the band.
  const forWidth = Math.max(0, room - OVERDUE_W - BOX_GAP - 3 * BOX_GAP) / (WORST_PIPE_UNITS * PIPE_UNIT);
  const units = shown.reduce((sum, quantity) => sum + quantity, 0);
  const forUke = units > 0 ? Math.max(0, room - overdueRoom - gaps) / (units * PIPE_UNIT) : Infinity;
  const scale = Math.max(0, Math.min(1, forWidth, forUke));
  const pipe = scaleLinear().domain([0, 1]).range([0, PIPE_UNIT * scale]);
  const stock = scaleLinear().domain([0, 1]).range([0, STOCK_UNIT * scale]);

  const ascent = ASCENT * f;
  const descent = DESCENT * f;
  const topBaseline = Math.ceil(ascent) + 1;
  const orderY = Math.round(topBaseline + descent + 2);
  const stockH = stock(inventory);
  const backlogH = stock(backlog);
  const up = Math.max(ascent + descent + BOX_H / 2 + 3, stockH + 4);
  const goodsY = Math.round(orderY + up);
  const midBaseline = goodsY - BOX_H / 2 - 1 - descent;
  const bottomBaseline = goodsY + BOX_H / 2 + 2 + ascent;
  const nodeBottom = Math.max(goodsY + backlogH + 4, bottomBaseline + descent);

  const boxes: Box[] = [];
  let cursor = nodeX - HEAD;
  // `cursor` ends left of the last box; the overdue box keeps clear of it (`room` holds both).
  for (const quantity of shown) {
    const w = pipe(quantity);
    boxes.push({ x: cursor - w, y: goodsY - BOX_H / 2, width: w, height: BOX_H });
    cursor -= w + BOX_GAP;
  }
  const typedBox = typed > 0 ? boxes.pop()! : null;
  // Overdue units have no known Uke: their box stands apart at the far end of the pipe.
  const overdueBox = overdue > 0 ? { x: PAD, y: goodsY - BOX_H / 2, width: OVERDUE_W, height: BOX_H } : null;

  const leftMax = nodeX - 6;
  const rightMin = nodeRight + 6;
  const wanted: Wanted[] = [
    // Row by row, the numbers first: an end label gives way to them.
    { key: "incoming", text: labels.incoming, weight: 600, row: 0, at: rightMin, anchor: "start", min: rightMin, max: width },
    { key: "order", text: labels.order, weight: 600, row: 0, at: leftMax, anchor: "end", min: 0, max: leftMax },
    { key: "downstream", text: labels.downstream, weight: 400, muted: true, row: 0, at: width, anchor: "end", min: rightMin, max: width },
    { key: "upstream", text: labels.upstream, weight: 400, muted: true, row: 0, at: 0, anchor: "start", min: 0, max: leftMax },
    { key: "delivery", text: labels.delivery, weight: 400, row: 1, at: leftMax, anchor: "end", min: 0, max: leftMax },
    { key: "shipped", text: labels.shipped, weight: 400, row: 1, at: rightMin, anchor: "start", min: rightMin, max: width },
  ];
  if (labels.overdue !== null && overdueBox) {
    wanted.push({
      key: "overdue",
      text: labels.overdue,
      weight: 600,
      row: 1,
      at: overdueBox.x + OVERDUE_W / 2,
      anchor: "middle",
      min: 0,
      max: leftMax,
    });
  }
  let stockAt = rightMin;
  for (const text of labels.stock) {
    wanted.push({ key: "stock", text, weight: 700, row: 2, at: stockAt, anchor: "start", min: rightMin, max: width });
    stockAt += textWidth(text, f, 700) + LABEL_GAP * f;
  }
  wanted.push({ key: "supplyLine", text: labels.supplyLine, weight: 600, row: 2, at: 0, anchor: "start", min: 0, max: leftMax });

  const baselines = [topBaseline, midBaseline, bottomBaseline];
  const taken: [number, number][][] = [[], [], []];
  const gap = LABEL_GAP * f;
  const placed: PlacedLabel[] = [];
  const wrapped: Wanted[] = [];
  for (const item of wanted) {
    const w = textWidth(item.text, f, item.weight);
    // A centred label (the overdue number over its box) keeps inside its room rather than wrapping.
    const x =
      item.anchor === "start"
        ? item.at
        : item.anchor === "end"
          ? item.at - w
          : Math.max(item.min, Math.min(item.at - w / 2, item.max - w));
    const free = taken[item.row]!.every(([a, b]) => x + w + gap <= a || x >= b + gap);
    if (x >= item.min - 0.01 && x + w <= item.max + 0.01 && free) {
      taken[item.row]!.push([x, x + w]);
      placed.push(label(item, x, baselines[item.row]!, w, false));
    } else {
      wrapped.push(item);
    }
  }

  // The rows under the band, in the order the labels were wanted, each label whole on one row and
  // on its own side: what belongs right of the node keeps to the right edge, the rest to the left.
  let bottom = Math.max(nodeBottom, bottomBaseline + descent) + 1;
  let baseline = bottom + 2 + ascent;
  let left = 0;
  let right = width;
  let empty = true;
  for (const item of wrapped) {
    const w = textWidth(item.text, f, item.weight);
    const onRight = item.min >= rightMin;
    if (!empty && (onRight ? right - w < left : left + w > right)) {
      baseline += ascent + descent + 2;
      left = 0;
      right = width;
    }
    const x = onRight ? Math.max(0, right - w) : left;
    placed.push(label(item, x, baseline, w, true));
    if (onRight) right = x - gap;
    else left = x + w + gap;
    empty = false;
    bottom = baseline + descent;
  }

  return {
    width,
    height: Math.ceil(bottom + 1),
    fontSize: f,
    scale,
    pipeUnit: PIPE_UNIT * scale,
    stockUnit: STOCK_UNIT * scale,
    node: { x: nodeX, y: orderY, width: NODE_W, height: nodeBottom - orderY },
    orderY,
    goodsY,
    stockBar: inventory > 0 ? { x: nodeX + 3, y: goodsY - stockH, width: NODE_W - 6, height: stockH } : null,
    backlogBar: backlog > 0 ? { x: nodeX + 3, y: goodsY, width: NODE_W - 6, height: backlogH } : null,
    boxes,
    typedBox,
    overdueBox,
    labels: placed,
  };
}

function label(item: Wanted, x: number, y: number, width: number, wrapped: boolean): PlacedLabel {
  return { key: item.key, text: item.text, x, y, width, weight: item.weight, muted: item.muted ?? false, wrapped };
}
