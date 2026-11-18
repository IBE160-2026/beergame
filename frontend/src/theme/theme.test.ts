import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import tokens from "./tokens.json";

const here = fileURLToPath(new URL(".", import.meta.url));
const DESIGN_MD = path.resolve(
  here,
  "../../../.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md",
);
const themeCss = fs.readFileSync(path.join(here, "theme.css"), "utf8");

/** Custom properties declared in theme.css. */
const vars = new Map(
  [...themeCss.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]),
);

/** "48px", "3rem" -> 48; unitless and em values are returned as they are. */
function toPx(value: string): number | string {
  const px = /^(-?[\d.]+)px$/.exec(value);
  if (px) return Number(px[1]);
  const rem = /^(-?[\d.]+)rem$/.exec(value);
  if (rem) return Number(rem[1]) * 16;
  return value;
}

describe("the token file", () => {
  it("is a copy of DESIGN.md's front matter", () => {
    const front = parse(fs.readFileSync(DESIGN_MD, "utf8").split(/^---\s*$/m)[1]);
    expect(tokens).toEqual({
      colors: front.colors,
      typography: front.typography,
      rounded: front.rounded,
      spacing: front.spacing,
    });
  });
});

describe("the theme", () => {
  it.each(Object.entries(tokens.colors))("holds colour %s", (name, value) => {
    expect(vars.get(`--color-${name}`)?.toUpperCase()).toBe(value.toUpperCase());
  });

  it.each(Object.entries(tokens.typography))("holds type role %s", (role, spec) => {
    const size = vars.get(`--text-${role}`);
    expect(size, `--text-${role}`).toMatch(/rem$/); // sizes grow with zoom (UX-DR3)
    expect(toPx(size!)).toBe(toPx(spec.fontSize));
    expect(vars.get(`--text-${role}--font-weight`)).toBe(spec.fontWeight);
    const lineHeight = "lineHeight" in spec ? spec.lineHeight : undefined;
    const themeLineHeight = vars.get(`--text-${role}--line-height`);
    if (lineHeight === undefined) expect(themeLineHeight).toBeUndefined();
    else expect(toPx(themeLineHeight!)).toBe(toPx(lineHeight));
    expect(spec.fontFamily).toBe("Source Sans 3");
  });

  it("uses Source Sans 3 as the font", () => {
    expect(vars.get("--font-sans")).toMatch(/^"Source Sans 3",/);
  });

  it.each(Object.entries(tokens.rounded))("holds radius %s", (name, value) => {
    expect(vars.get(`--radius-${name}`)).toBe(value);
  });

  it.each(Object.entries(tokens.spacing))("holds spacing %s", (name, value) => {
    expect(vars.get(`--spacing-${name}`)).toBe(value);
  });

  it("holds no token that is not in the token file", () => {
    const known = new Set([
      "--font-sans",
      ...Object.keys(tokens.colors).map((n) => `--color-${n}`),
      ...Object.keys(tokens.rounded).map((n) => `--radius-${n}`),
      ...Object.keys(tokens.spacing).map((n) => `--spacing-${n}`),
      ...Object.keys(tokens.typography).flatMap((r) => [
        `--text-${r}`,
        `--text-${r}--line-height`,
        `--text-${r}--font-weight`,
      ]),
    ]);
    expect([...vars.keys()].filter((v) => !known.has(v))).toEqual([]);
  });

  it("resets Tailwind's default colours, sizes, radii, shadows and letter-spacing, and emits every token", () => {
    for (const ns of ["color", "text", "radius", "shadow", "inset-shadow", "drop-shadow", "text-shadow", "tracking"]) {
      expect(themeCss).toContain(`--${ns}-*: initial;`);
    }
    expect(themeCss).toContain("@theme static {");
  });

  it("gives proportional figures only to figure-hero and figure-amplification", () => {
    const withoutComments = themeCss.replace(/\/\*[\s\S]*?\*\//g, "");
    const rules = [...withoutComments.matchAll(/([^{}]+)\{\s*font-variant-numeric:\s*([^;]+);/g)];
    expect(rules).toHaveLength(1);
    expect(rules[0][1].split(",").map((s) => s.trim())).toEqual([
      ".text-figure-hero",
      ".text-figure-amplification",
    ]);
    expect(rules[0][2]).toBe("lining-nums proportional-nums");
    const globals = fs.readFileSync(path.join(here, "../app/globals.css"), "utf8");
    expect(globals).toMatch(/html\s*\{[^}]*font-variant-numeric:\s*lining-nums tabular-nums;/);
  });
});
