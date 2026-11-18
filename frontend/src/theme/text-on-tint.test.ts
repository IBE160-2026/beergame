import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { contrastRatio } from "./contrast";
import {
  CONTROL_FILLS,
  type ColourToken,
  colourHex,
  isAllowedTextOn,
  TEXT_ON_TINT,
} from "./text-on-tint";
import tokens from "./tokens.json";

const pairs = (table: typeof TEXT_ON_TINT) =>
  Object.entries(table).flatMap(([bg, texts]) =>
    (texts ?? []).map((text) => [bg as ColourToken, text] as const),
  );

describe("text on tints", () => {
  it.each(pairs(TEXT_ON_TINT))("%s background, %s text is at least 4.5:1", (bg, text) => {
    expect(contrastRatio(colourHex(bg), colourHex(text))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(pairs(CONTROL_FILLS))("control fill %s with %s label is at least 4.5:1", (bg, text) => {
    expect(contrastRatio(colourHex(bg), colourHex(text))).toBeGreaterThanOrEqual(4.5);
  });

  it("matches the ratios DESIGN.md prints for text on paper", () => {
    const r = (t: ColourToken) => Math.round(contrastRatio(colourHex("paper"), colourHex(t)) * 10) / 10;
    expect([r("ink"), r("ink-secondary"), r("ink-muted"), r("lager"), r("restordre")]).toEqual([
      14.6, 7.3, 5.2, 5.6, 5.5,
    ]);
  });

  it("never allows projection as text, a line colour only", () => {
    expect(isAllowedTextOn("paper", "projection")).toBe(false);
  });

  // DESIGN.md's "Fails, never use" column.
  it.each([
    ["paper", "order-history"],
    ["lager-fill", "ink-muted"],
    ["lager-fill", "lager"],
    ["restordre-fill", "restordre"],
    ["restordre-fill", "order-history"],
    ["net-neg-1", "ink-secondary"],
    ["flow-2", "ink-secondary"],
    ["net-pos-3", "ink"],
    ["hairline", "ink-muted"],
  ] as const)("rejects %s background with %s text", (bg, text) => {
    expect(isAllowedTextOn(bg, text)).toBe(false);
    expect(contrastRatio(colourHex(bg), colourHex(text))).toBeLessThan(4.5);
  });
});

// Every text colour the components set on a background must be a pair from the table.
describe("class pairs in the components", () => {
  const colours = new Set(Object.keys(tokens.colors));
  const srcDir = path.resolve(fileURLToPath(new URL(".", import.meta.url)), "..");
  const files: string[] = [];
  const walk = (d: string) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.name.endsWith(".tsx") && !e.name.includes(".test.")) files.push(full);
    }
  };
  walk(srcDir);

  /** For each variant (`""`, `hover`, `aria-disabled` …) the background and text colour token set. */
  function colourClasses(classString: string) {
    const byVariant = new Map<string, { bg?: string; text?: string }>();
    for (const cls of classString.split(/\s+/)) {
      const i = cls.lastIndexOf(":");
      const variant = i < 0 ? "" : cls.slice(0, i);
      const utility = i < 0 ? cls : cls.slice(i + 1);
      const m = /^(bg|text)-(.+)$/.exec(utility);
      if (!m || !colours.has(m[2])) continue;
      const entry = byVariant.get(variant) ?? {};
      entry[m[1] as "bg" | "text"] = m[2];
      byVariant.set(variant, entry);
    }
    return byVariant;
  }

  it("found the component files", () => {
    expect(files.length).toBeGreaterThan(0);
  });

  it("uses only text-on-background pairs from the table", () => {
    const outside: string[] = [];
    for (const file of files) {
      const source = fs.readFileSync(file, "utf8");
      for (const [, classString] of source.matchAll(/"([^"\n]*)"/g)) {
        const byVariant = colourClasses(classString);
        const base = byVariant.get("") ?? {};
        for (const [variant, { bg, text }] of byVariant) {
          const background = (bg ?? base.bg ?? "paper") as ColourToken;
          const fg = (text ?? base.text ?? "ink") as ColourToken;
          if (!isAllowedTextOn(background, fg)) {
            outside.push(`${path.basename(file)} [${variant || "idle"}] ${fg} on ${background}`);
          }
        }
      }
    }
    expect(outside).toEqual([]);
  });

  it("catches a pair outside the table", () => {
    const byVariant = colourClasses("bg-lager-fill text-ink-muted");
    const { bg, text } = byVariant.get("")!;
    expect(isAllowedTextOn(bg as ColourToken, text as ColourToken)).toBe(false);
  });
});
