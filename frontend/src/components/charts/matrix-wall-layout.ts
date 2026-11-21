import type { ColourToken } from "./palette";
import { textWidth } from "./chain-band-layout";

/** A Netto lager matrix step (DESIGN.md → Colour → Matrix steps): |v| 1–9, 10–19, 20–34, 35+. */
export type NetStep = "zero" | `pos-${1 | 2 | 3 | 4}` | `neg-${1 | 2 | 3 | 4}`;

export function netStep(value: number): NetStep {
  if (value === 0) return "zero";
  const size = Math.abs(value);
  const bin = size < 10 ? 1 : size < 20 ? 2 : size < 35 ? 3 : 4;
  return value > 0 ? `pos-${bin}` : `neg-${bin}`;
}

/** The steps in legend order, most below zero first (DESIGN.md → Components → Matrisevegg). */
export const NET_STEPS: readonly NetStep[] = [
  "neg-4",
  "neg-3",
  "neg-2",
  "neg-1",
  "zero",
  "pos-1",
  "pos-2",
  "pos-3",
  "pos-4",
];

/** A flow step (DESIGN.md → Colour → Matrix steps, «Flows / orders»): under 5 no fill, then
 * 5–9, 10–19, 20–29 and 30+, for the Ordre and Kost per uke cells (Story 7.4). */
export type FlowStep = "flow-none" | `flow-${1 | 2 | 3 | 4}`;

export function flowStep(value: number): FlowStep {
  if (value < 5) return "flow-none";
  return value < 10 ? "flow-1" : value < 20 ? "flow-2" : value < 30 ? "flow-3" : "flow-4";
}

/** The flow steps in legend order. */
export const FLOW_STEPS: readonly FlowStep[] = ["flow-none", "flow-1", "flow-2", "flow-3", "flow-4"];

/** Which scale the cells are drawn in: Netto lager's signed steps or the flow steps. */
export type WallScale = "net" | "flow";

export type WallStep = NetStep | FlowStep;

export function stepOf(scale: WallScale, value: number): WallStep {
  return scale === "flow" ? flowStep(value) : netStep(value);
}

export function stepsOf(scale: WallScale): readonly WallStep[] {
  return scale === "flow" ? FLOW_STEPS : NET_STEPS;
}

export function stepFill(step: WallStep): ColourToken {
  if (step === "flow-none") return "paper";
  return (step.startsWith("flow-") ? step : `net-${step}`) as ColourToken;
}

/** The cell-text rule (NFR-6, UX-DR2): `ink` on zero, no fill and steps 1–2, `paper` on 3–4. */
export function stepText(step: WallStep): "ink" | "paper" {
  return step.endsWith("3") || step.endsWith("4") ? "paper" : "ink";
}

/** The Skjelett bar of a row whose weeks are on their way, in cells. */
export const SKELETON_CELLS = 8;

/** The smallest text in the wall (`matrix-cell-min`, DESIGN.md → Typography): 9 px. */
export const CELL_FONT_MIN = 9;

export type CellText = { kind: "number" | "minus" | "blank"; text: string };

/**
 * What a cell prints (DESIGN.md → Components → Matrisevegg): its signed number when the number
 * fits with 1 px to spare on each side; otherwise a below-zero cell prints only a true minus «−»,
 * centred, and any other cell stays blank. `formatted` is the number as the one formatter writes
 * it («−13»), so the sign is a true minus.
 */
export function cellText(value: number, formatted: string, cellWidth: number, fontSize: number): CellText {
  if (textWidth(formatted, fontSize) + 2 <= cellWidth) return { kind: "number", text: formatted };
  if (value < 0) return { kind: "minus", text: "−" };
  return { kind: "blank", text: "" };
}

export type WallSizes = {
  /** Text outside the cells (labels, Uke header): the caption size at the current text zoom. */
  fontSize: number;
  /** Text inside the cells: `matrix-cell-min` at 13 px, growing with text zoom. */
  cellFont: number;
  rowHeight: number;
  headerHeight: number;
  groupHeight: number;
  labelWidth: number;
  /** Where the row's figure (kjedekost) ends, right-aligned inside the label column. */
  figureRight: number;
  cellWidth: number;
  columns: number;
  detailWidth: number;
  /** The rows draw their short note: the full ones would make the drawing wider than the width
   * passed in while the Uker fit (Story 7.6). */
  shortDetail: boolean;
  /** The whole drawing; wider than the width passed in when the Uker need more room. */
  width: number;
};

const GAP = 0.75; // em between label and figure, and around the detail text

/** A row's note after its cells (Story 7.6): how many cells the row has, its full and its short
 * form. */
export type WallNote = { cells: number; full: string; short: string };

/**
 * The wall's sizes from the width the caller passes in (AD-18) and the text size: the label
 * column fits the longest label and figure, the detail column the longest detail text, and the
 * Uker share what is left, each at least a near-square cell and at most two rows wide. When
 * `width` is too narrow the drawing is wider and its region scrolls (UX-DR75).
 */
export function wallSizes(input: {
  width: number;
  fontSize: number;
  columns: number;
  labels: readonly string[];
  figures: readonly string[];
  details: readonly string[];
  /**
   * Each row's note with its number of cells and a short form (Story 7.6). Given, a note is laid
   * after its own row's cells, and the rows draw the short forms when a full one would run past
   * `width` at the narrowest cells; `details` is then not read.
   */
  notes?: readonly WallNote[];
  /** Labels that take the whole game column, figure included («Kjedekost/uke, snitt»). */
  spans?: readonly string[];
}): WallSizes {
  const { width, fontSize } = input;
  // No game with a Uke yet: no Uke column at all, and the width math divides by one.
  const columns = Math.max(0, input.columns);
  const cellFont = Math.max(CELL_FONT_MIN, Math.round((fontSize * CELL_FONT_MIN) / 13));
  const rowHeight = Math.ceil(fontSize * 1.35);
  const gap = Math.round(fontSize * GAP);
  const widest = (texts: readonly string[], weight: 400 | 600 = 400) =>
    texts.reduce((most, text) => Math.max(most, textWidth(text, fontSize, weight)), 0);
  const labelPart = widest(input.labels);
  const figurePart = widest(input.figures);
  const labelWidth = Math.max(labelPart + (figurePart > 0 ? gap + figurePart : 0), widest(input.spans ?? [])) + gap;
  const minCell = Math.ceil(rowHeight * 0.85);
  const maxCell = rowHeight * 2;
  const notes = input.notes;
  // The full notes when each ends inside `width` after its row's cells at their narrowest, else
  // the short ones: a note never runs past the region's edge while the Uker themselves fit.
  const noteEnd = (cell: number, pick: (note: WallNote) => string) =>
    (notes ?? []).reduce(
      (most, note) => Math.max(most, note.cells * cell + 2 * gap + textWidth(pick(note), fontSize)),
      0,
    );
  const shortDetail = notes !== undefined && labelWidth + noteEnd(minCell, (note) => note.full) > width;
  const chosen = (note: WallNote) => (shortDetail ? note.short : note.full);
  const detail = notes ? widest(notes.map(chosen)) : widest(input.details);
  const detailWidth = detail > 0 ? detail + 2 * gap : 0;
  const room = Math.floor((width - labelWidth - detailWidth) / Math.max(1, columns));
  const cellWidth = Math.max(minCell, Math.min(maxCell, room));
  const cellsEnd = labelWidth + Math.max(columns, SKELETON_CELLS) * cellWidth;
  return {
    fontSize,
    cellFont,
    rowHeight,
    headerHeight: Math.ceil(fontSize * 1.7),
    groupHeight: Math.ceil(fontSize * 2.2),
    labelWidth,
    figureRight: labelWidth - gap,
    cellWidth,
    columns,
    detailWidth,
    shortDetail,
    // Room for a loading row's Skjelett bar (8 cells) also before any game has a Uke; with
    // `notes`, each note after its own row's cells.
    width: notes
      ? Math.max(cellsEnd, labelWidth + noteEnd(cellWidth, chosen))
      : cellsEnd + detailWidth,
  };
}

/** The Uker whose number the header prints: every one when they fit, else Uke 1 and every
 * fifth (as drawn in `08-laerer-oversikt.png`). */
export function headerWeeks(columns: number, cellWidth: number, fontSize: number): number[] {
  const all = Array.from({ length: columns }, (_, i) => i + 1);
  if (textWidth(String(columns), fontSize) + 2 <= cellWidth) return all;
  return all.filter((week) => week === 1 || week % 5 === 0);
}

/** A cell the keyboard can reach: the game's id and its Uke (1-based). */
export type WallPosition = { id: string; week: number };

/**
 * Where an arrow, Home or End key moves focus (EXPERIENCE.md → Matrisevegg → Keyboard): left and
 * right cell by cell within the row, up and down to the nearest game row with cells, keeping the
 * Uke where that row has it and else its last; Home and End to the row's first and last Uke.
 * `rows` are the game rows in drawn order with their number of cells. Returns null for any
 * other key, and the same position at an edge.
 */
export function moveFocus(
  rows: readonly { id: string; cells: number }[],
  at: WallPosition,
  key: string,
): WallPosition | null {
  const reachable = rows.filter((row) => row.cells > 0);
  const index = reachable.findIndex((row) => row.id === at.id);
  if (index < 0) return null;
  const row = reachable[index]!;
  const clamp = (target: { cells: number }, week: number) => Math.min(Math.max(1, week), target.cells);
  switch (key) {
    case "ArrowLeft":
      return { id: row.id, week: clamp(row, at.week - 1) };
    case "ArrowRight":
      return { id: row.id, week: clamp(row, at.week + 1) };
    case "Home":
      return { id: row.id, week: 1 };
    case "End":
      return { id: row.id, week: row.cells };
    case "ArrowUp": {
      const target = reachable[Math.max(0, index - 1)]!;
      return { id: target.id, week: clamp(target, at.week) };
    }
    case "ArrowDown": {
      const target = reachable[Math.min(reachable.length - 1, index + 1)]!;
      return { id: target.id, week: clamp(target, at.week) };
    }
    default:
      return null;
  }
}
