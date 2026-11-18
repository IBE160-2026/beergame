import tokens from "./tokens.json";

export type ColourToken = keyof typeof tokens.colors;

const ON_PAPER = ["ink", "ink-secondary", "ink-muted", "lager", "restordre"] as const;

/**
 * DESIGN.md → Colors → Text on tints: the only text colours allowed on each background.
 * Every pair is at least 4.5:1 (checked by text-on-tint.test.ts).
 */
export const TEXT_ON_TINT: Readonly<Partial<Record<ColourToken, readonly ColourToken[]>>> = {
  paper: ON_PAPER,
  "future-tint": ON_PAPER,
  "lager-fill": ["ink", "ink-secondary"],
  // The zero bin of the Netto lager scale (DESIGN.md → Matrix steps) prints its 0 in ink.
  "net-zero": ["ink"],
  "restordre-fill": ["ink", "ink-secondary"],
  "net-neg-1": ["ink"],
  "net-pos-1": ["ink"],
  "flow-1": ["ink"],
  "net-neg-2": ["ink"],
  "net-pos-2": ["ink"],
  "flow-2": ["ink"],
  "net-neg-3": ["paper"],
  "net-neg-4": ["paper"],
  "net-pos-3": ["paper"],
  "net-pos-4": ["paper"],
  "flow-3": ["paper"],
  "flow-4": ["paper"],
  hairline: ["ink"],
};

/**
 * DESIGN.md → Components → Interaction states: the filled control states. Idle is an `ink` fill with
 * a `paper` label (14.6:1), and pressed is an `ink-secondary` fill with a `paper` label (7.3:1).
 */
export const CONTROL_FILLS: Readonly<Partial<Record<ColourToken, readonly ColourToken[]>>> = {
  ink: ["paper"],
  "ink-secondary": ["paper"],
};

export function isAllowedTextOn(background: ColourToken, text: ColourToken): boolean {
  return (
    (TEXT_ON_TINT[background]?.includes(text) ?? false) ||
    (CONTROL_FILLS[background]?.includes(text) ?? false)
  );
}

export function colourHex(token: ColourToken): string {
  return tokens.colors[token];
}
