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
  /** The Order is a KI-spiller's, not the Student's (Story 8.4): drawn at regular weight. */
  orderByAi?: boolean;
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
  /** A neighbour's numbers that Information visibility shows (Story 6.21, UX-DR24): «Lager 12»,
   * «Restordre 3», at that neighbour's end; none when its view is off. */
  upstreamNumbers?: readonly string[];
  downstreamNumbers?: readonly string[];
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
  | "overdue"
  | "upstreamNumbers"
  | "downstreamNumbers"
  | "role"
  | "roleNumbers";

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
  /** Drawn flush with the right end of its box (`x + width`), so a right-edge column of labels
   * lines up although the real text is narrower than the estimate. */
  alignEnd?: boolean;
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

/** The labels that wrap together (see `bandLayout`), and their left-to-right order in the band. */
const GROUP: Partial<Record<LabelKey, string>> = { upstream: "up", order: "up", downstream: "down", incoming: "down", stock: "stock" };
const BAND_ORDER: Record<LabelKey, number> = {
  upstream: 0,
  order: 1,
  incoming: 2,
  downstream: 3,
  delivery: 4,
  shipped: 5,
  stock: 6,
  overdue: 7,
  supplyLine: 8,
  upstreamNumbers: 9,
  downstreamNumbers: 10,
  role: 11,
  roleNumbers: 12,
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
    { key: "order", text: labels.order, weight: labels.orderByAi ? 400 : 600, row: 0, at: leftMax, anchor: "end", min: 0, max: leftMax },
    { key: "delivery", text: labels.delivery, weight: 400, row: 1, at: leftMax, anchor: "end", min: 0, max: leftMax },
    { key: "shipped", text: labels.shipped, weight: 400, row: 1, at: rightMin, anchor: "start", min: rightMin, max: width },
  ];
  // An end label gives way to the numbers; one whose neighbour's numbers show (Story 6.21) heads
  // that neighbour's block under the band instead.
  const upBlock = labels.upstreamNumbers !== undefined;
  const downBlock = labels.downstreamNumbers !== undefined;
  if (!downBlock) {
    wanted.splice(2, 0, { key: "downstream", text: labels.downstream, weight: 400, muted: true, row: 0, at: width, anchor: "end", min: rightMin, max: width });
  }
  if (!upBlock) {
    wanted.splice(downBlock ? 2 : 3, 0, { key: "upstream", text: labels.upstream, weight: 400, muted: true, row: 0, at: 0, anchor: "start", min: 0, max: leftMax });
  }
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
  const gap = LABEL_GAP * f;
  // Labels that belong together wrap together (Epic 6): the order going out with the upstream
  // end, the order coming in with the downstream end, and the stock labels with each other. A
  // group with one label short of room wraps whole, so no end label stays behind its number.
  const place = (forced: ReadonlySet<string>) => {
    const taken: [number, number][][] = [[], [], []];
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
      const group = GROUP[item.key];
      if (!(group && forced.has(group)) && x >= item.min - 0.01 && x + w <= item.max + 0.01 && free) {
        taken[item.row]!.push([x, x + w]);
        placed.push(label(item, x, baselines[item.row]!, w, false));
      } else {
        wrapped.push(item);
      }
    }
    return { placed, wrapped };
  };
  let { placed, wrapped } = place(new Set());
  const broken = new Set(wrapped.map((item) => GROUP[item.key]).filter((group) => group !== undefined));
  if (broken.size > 0) ({ placed, wrapped } = place(broken));

  // The wrapped labels as units: a group's labels together, in the band's left-to-right order, at
  // the place of its first label; every other label on its own.
  const wrapUnits: Wanted[][] = [];
  for (const item of wrapped) {
    const group = GROUP[item.key];
    if (group === undefined) wrapUnits.push([item]);
    else if (!wrapUnits.some((unit) => GROUP[unit[0]!.key] === group)) {
      const unit = wrapped.filter((other) => GROUP[other.key] === group).sort((a, b) => BAND_ORDER[a.key] - BAND_ORDER[b.key]);
      const whole = unit.reduce((sum, other) => sum + textWidth(other.text, f, other.weight), 0) + gap * (unit.length - 1);
      // A group wider than the band takes a row per label, still one after the other.
      if (whole <= width) wrapUnits.push(unit);
      else wrapUnits.push(...unit.map((other) => [other]));
    }
  }

  // The rows under the band, in the order the labels were wanted, each unit whole on one row and
  // on its own side: what belongs right of the node keeps to the right edge, the rest to the left.
  let bottom = Math.max(nodeBottom, bottomBaseline + descent) + 1;
  let baseline = bottom + 2 + ascent;
  let left = 0;
  let right = width;
  let empty = true;
  for (const unit of wrapUnits) {
    const widths = unit.map((item) => textWidth(item.text, f, item.weight));
    const w = widths.reduce((sum, one) => sum + one, 0) + gap * (unit.length - 1);
    const onRight = unit[0]!.min >= rightMin;
    if (!empty && (onRight ? right - w < left : left + w > right)) {
      baseline += ascent + descent + 2;
      left = 0;
      right = width;
    }
    let x = onRight ? Math.max(0, right - w) : left;
    const start = x;
    unit.forEach((item, i) => {
      placed.push(label(item, x, baseline, widths[i]!, true));
      x += widths[i]! + gap;
    });
    if (onRight) right = start - gap;
    else left = start + w + gap;
    empty = false;
    bottom = baseline + descent;
  }

  // The neighbours' blocks (Story 6.21, UX-DR24), under everything else and kept together: the
  // end label («Distributør, Uke 11») on its own row, then the numbers. The upstream block keeps
  // to the left edge, the downstream block to the right; side by side when both fit, else stacked.
  const rowStep = ascent + descent + 2;
  const blocks = [
    upBlock ? { side: "left" as const, title: labels.upstream, numbers: labels.upstreamNumbers!, key: "upstream" as const } : null,
    downBlock ? { side: "right" as const, title: labels.downstream, numbers: labels.downstreamNumbers!, key: "downstream" as const } : null,
  ].filter((block) => block !== null);
  const lines = blocks.map((block) => {
    const rows: Wanted[][] = [[{ key: block.key, text: block.title, weight: 400, muted: true, row: 0, at: 0, anchor: "start", min: 0, max: width }]];
    let current: Wanted[] = [];
    let used = 0;
    for (const text of block.numbers) {
      const w = textWidth(text, f, 400);
      if (current.length > 0 && used + gap + w > width) {
        rows.push(current);
        current = [];
        used = 0;
      }
      current.push({ key: block.key === "upstream" ? "upstreamNumbers" : "downstreamNumbers", text, weight: 400, row: 0, at: 0, anchor: "start", min: 0, max: width });
      used += (used > 0 ? gap : 0) + w;
    }
    if (current.length > 0) rows.push(current);
    const rowWidth = (row: Wanted[]) => row.reduce((sum, item, i) => sum + (i > 0 ? gap : 0) + textWidth(item.text, f, item.weight), 0);
    return { side: block.side, rows, widest: Math.max(...rows.map(rowWidth)), rowWidth };
  });
  if (lines.length > 0) {
    let top = (empty ? bottom : baseline + descent) + 0.4 * f;
    const together = lines.length === 2 && lines[0]!.widest + 2 * gap + lines[1]!.widest <= width;
    for (const block of lines) {
      let rowBaseline = top + 2 + ascent;
      for (const row of block.rows) {
        let x = block.side === "left" ? 0 : Math.max(0, width - block.rowWidth(row));
        for (const item of row) {
          const w = textWidth(item.text, f, item.weight);
          // The downstream block keeps flush with the right edge, title and numbers alike.
          placed.push({ ...label(item, x, rowBaseline, w, true), ...(block.side === "right" ? { alignEnd: true } : {}) });
          x += w + gap;
        }
        bottom = Math.max(bottom, rowBaseline + descent);
        rowBaseline += rowStep;
      }
      // Stacked, the next block keeps the same space above it as the first.
      if (!together) top = bottom + 0.4 * f;
    }
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

/** One Role in the four-Role band, upstream first. */
export type ChainNodeInput = {
  /** «Fabrikk». */
  label: string;
  /** «Restordre 3», «Lager 12», or both for a capped Seat that holds both (Story 6.22). */
  numbers: readonly string[];
  inventory: number;
  backlog: number;
  /** The viewer's own Role: a 1.4 px `ink` border (DESIGN.md → Kjedebånd). */
  own: boolean;
};

export type ChainBandInput = {
  width: number;
  fontSize: number;
  /** The Roles, upstream first (Fabrikk … Detaljist). */
  nodes: readonly ChainNodeInput[];
  /** The Order on the order line in each gap, upstream first: each Role's own Order in the gap
   * left of it, then the customers' order in the gap at the right end (`nodes.length + 1`). */
  orders: readonly string[];
  /** På vei into each Role, on the goods line in the gap left of it (`nodes.length`); a Role
   * with nothing on the way gives null and gets no box. */
  supplyLines: readonly (string | null)[];
  /** The largest stock or backlog in any Role and Uke of the game, so the bars keep one scale
   * and the band one height while the Uke changes. */
  maxUnits: number;
  /** «Produksjon» and «Kundene». */
  upstream: string;
  downstream: string;
};

export type ChainNodeLayout = { box: Box; stockBar: Box | null; backlogBar: Box | null; own: boolean };

export type ChainBandLayout = {
  width: number;
  height: number;
  fontSize: number;
  /** px per unit of stock or backlog. */
  stockUnit: number;
  orderY: number;
  goodsY: number;
  nodes: ChainNodeLayout[];
  /** Each gap's left and right edge, upstream first (`nodes.length + 1`). */
  gaps: { x0: number; x1: number }[];
  /** The box on the goods line of each gap with goods on the way. */
  pipeBoxes: Box[];
  labels: PlacedLabel[];
  /** The node label blocks were set on two rows, every other one lower, for want of room. */
  staggered: boolean;
};

/** «Restordre 34» as «Restordre» and «34», for a narrow band; text with no space stays whole. */
function splitNumber(text: string): string[] {
  const at = text.lastIndexOf(" ");
  return at > 0 ? [text.slice(0, at), text.slice(at + 1)] : [text];
}

/** The tallest stock or backlog bar of the four-Role band, in px. */
const CHAIN_BAR_MAX = 44;
const PIPE_BOX_W = 14;

/**
 * The four-Role Kjedebånd (Story 9.5, UX-DR15, UX-DR31, DESIGN.md → Kjedebånd: «The full four-Role
 * chain (Debrief, Faglærer) adds Produksjon at the left and Kundene at the right»). Upstream at the
 * left. From the top: the end labels; each gap's Order over the order line (right to left); the
 * nodes on the goods line with stock above it and backlog below; each gap's På vei over a box on
 * the goods line; under each node its Role and numbers. The nodes stand evenly, with equal gaps
 * between them and at both ends. A node label block that would meet its neighbour's sets every
 * other block one block lower, so no two node label blocks overlap. The Orders and På vei in the
 * gaps are centred in their gap and kept inside the band; they fit a gap at up to two digits at
 * 320 px with 200 % text (wider numbers at that size may reach a node). A pure function of its
 * input.
 */
export function chainLayout(input: ChainBandInput): ChainBandLayout {
  const { width, fontSize: f, nodes, orders, supplyLines, maxUnits } = input;
  const n = nodes.length;
  const nodeW = width < 480 ? 32 : NODE_W;
  const gapW = Math.max(0, (width - n * nodeW) / (n + 1));
  const ascent = ASCENT * f;
  const descent = DESCENT * f;
  const rowStep = ascent + descent + 2;
  const unit = maxUnits > 0 ? Math.min(STOCK_UNIT, CHAIN_BAR_MAX / maxUnits) : STOCK_UNIT;
  const barMax = maxUnits * unit;

  const endsBaseline = Math.ceil(ascent) + 1;
  const ordersBaseline = endsBaseline + rowStep;
  const orderY = Math.round(ordersBaseline + descent + 2);
  const goodsY = Math.round(orderY + Math.max(ascent + descent + BOX_H / 2 + 3, barMax + 4));
  const supplyBaseline = goodsY - BOX_H / 2 - 1 - descent;
  const nodeBottom = Math.round(goodsY + barMax + 4);

  const gaps = Array.from({ length: n + 1 }, (_, i) => {
    const x0 = i * (gapW + nodeW);
    return { x0, x1: x0 + gapW };
  });
  const placed: PlacedLabel[] = [];
  const put = (key: LabelKey, text: string, x: number, y: number, weight: 400 | 600 | 700, muted = false) => {
    const w = textWidth(text, f, weight);
    placed.push({ key, text, x, y, width: w, weight, muted, wrapped: false });
  };
  const centred = (text: string, at: number, weight: 400 | 600 | 700) =>
    Math.max(0, Math.min(at - textWidth(text, f, weight) / 2, width - textWidth(text, f, weight)));

  put("upstream", input.upstream, 0, endsBaseline, 400, true);
  put("downstream", input.downstream, width - textWidth(input.downstream, f, 400), endsBaseline, 400, true);
  orders.forEach((text, i) => {
    const gap = gaps[i];
    if (gap) put("order", text, centred(text, (gap.x0 + gap.x1) / 2, 600), ordersBaseline, 600);
  });
  const pipeBoxes: Box[] = [];
  supplyLines.forEach((text, i) => {
    const gap = gaps[i];
    if (!gap || text === null) return;
    const mid = (gap.x0 + gap.x1) / 2;
    const w = Math.min(PIPE_BOX_W, Math.max(4, gapW - 10));
    pipeBoxes.push({ x: mid - w / 2, y: goodsY - BOX_H / 2, width: w, height: BOX_H });
    put("supplyLine", text, centred(text, mid, 400), supplyBaseline, 400);
  });

  const layoutNodes = nodes.map((node, i): ChainNodeLayout => {
    const x = gaps[i]!.x1;
    // A held unit always shows, however large the game's largest stock or backlog.
    const stockH = Math.max(1, node.inventory * unit);
    const backlogH = Math.max(1, node.backlog * unit);
    return {
      box: { x, y: orderY, width: nodeW, height: nodeBottom - orderY },
      stockBar: node.inventory > 0 ? { x: x + 3, y: goodsY - stockH, width: nodeW - 6, height: stockH } : null,
      backlogBar: node.backlog > 0 ? { x: x + 3, y: goodsY, width: nodeW - 6, height: backlogH } : null,
      own: node.own,
    };
  });

  // Each node's label block (its Role, then its numbers), centred on it and kept inside the band.
  // The first arrangement with no two blocks meeting wins: all on one row; every other block one
  // block lower; the same with each number split from its word («Restordre» over «34»); at last
  // each block on a row of its own, which always fits.
  const gap = LABEL_GAP * f;
  const blocksOf = (split: boolean) =>
    nodes.map((node, i) => {
      const numbers = split ? node.numbers.flatMap((text) => splitNumber(text)) : node.numbers;
      const lines = [
        { key: "role" as const, text: node.label, weight: 600 as const },
        ...numbers.map((text) => ({ key: "roleNumbers" as const, text, weight: 400 as const })),
      ];
      const widest = Math.max(...lines.map((line) => textWidth(line.text, f, line.weight)));
      const centre = gaps[i]!.x1 + nodeW / 2;
      const left = Math.max(0, Math.min(centre - widest / 2, width - widest));
      return { lines, left, right: left + widest, centre };
    });
  type Block = ReturnType<typeof blocksOf>[number];
  const clear = (blocks: Block[], level: (i: number) => number) =>
    blocks.every((a, i) => blocks.every((b, j) => j <= i || level(i) !== level(j) || a.right + gap <= b.left));
  const arrangements: { split: boolean; level: (i: number) => number }[] = [
    { split: false, level: () => 0 },
    { split: false, level: (i) => i % 2 },
    { split: true, level: (i) => i % 2 },
    { split: true, level: (i) => i },
  ];
  const chosen =
    arrangements.find((arrangement) => clear(blocksOf(arrangement.split), arrangement.level)) ?? arrangements[arrangements.length - 1]!;
  const blocks = blocksOf(chosen.split);
  const staggered = blocks.some((_, i) => chosen.level(i) > 0);
  const blockRows = Math.max(1, ...blocks.map((block) => block.lines.length));
  let bottom = nodeBottom;
  blocks.forEach((block, i) => {
    const lower = chosen.level(i) * (blockRows * rowStep + 0.2 * f);
    block.lines.forEach((line, row) => {
      const w = textWidth(line.text, f, line.weight);
      const x = Math.max(0, Math.min(block.centre - w / 2, width - w));
      const y = nodeBottom + 2 + ascent + lower + row * rowStep;
      put(line.key, line.text, x, y, line.weight);
      bottom = Math.max(bottom, y + descent);
    });
  });

  return {
    width,
    height: Math.ceil(bottom + 1),
    fontSize: f,
    stockUnit: unit,
    orderY,
    goodsY,
    nodes: layoutNodes,
    gaps,
    pipeBoxes,
    labels: placed,
    staggered,
  };
}
