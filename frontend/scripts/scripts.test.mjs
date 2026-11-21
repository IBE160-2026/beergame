import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { renderTheme, readTokens, THEME_PATH } from "./build-theme.mjs";
import { checkRepo, checkText, stringsFromSource, textFromTemplate } from "./check-copy.mjs";
import { lintRepo, lintText } from "./lint-colours.mjs";

describe("theme generator", () => {
  it("theme.css is up to date with tokens.json (run `npm run theme`)", () => {
    expect(fs.readFileSync(THEME_PATH, "utf8")).toBe(renderTheme(readTokens()));
  });
});

describe("copy check", () => {
  it("passes on the repo", () => {
    expect(checkRepo()).toEqual([]);
  });

  it.each([
    ["Bra jobba!", "exclamation"],
    ["Kasser øl", "ol"],
    ["Øl på lager", "ol"],
    ["ølkasser", "ol"],
    ["Den optimale ordren", "optimal"],
    ["Ikke en fasit", "fasit"],
    ["Velkommen til Beer Game", "beer-game"],
    ["bullwhip-effekten", "bullwhip"],
  ])("fails on %j (%s)", (text, rule) => {
    expect(checkText(text)).toContain(rule);
  });

  it.each(["ØL-spillet", "Velkommen til ØL-spillet.", "Følg kolonnen.", "Bølgen", "Støl"])(
    "passes %j",
    (text) => {
      expect(checkText(text)).toEqual([]);
    },
  );

  it("allows «Beer Game» and «bullwhip» after the Debrief, but no other breach", () => {
    expect(checkText("bullwhip-effekten i Beer Game", { preDebrief: false })).toEqual([]);
    expect(checkText("Fasit!", { preDebrief: false })).toEqual(["exclamation", "fasit"]);
  });

  it("reads string values but not keys, imports or comments, and knows each string's section", () => {
    const strings = stringsFromSource(
      `import x from "bad!";\n// optimal!\nexport const nb = { "a!": "ok", debrief: { b: \`Uke \${n}!\` } };`,
      "nb.ts",
    );
    expect(strings.map((s) => [s.text, s.section])).toEqual([
      ["ok", "a!"],
      ["Uke ", "debrief"],
      ["!", "debrief"],
    ]);
  });

  it("reads JSX text in the print route", () => {
    const strings = stringsFromSource(`export default () => <p>Hei {x} der!</p>;`, "page.tsx");
    expect(strings.map((s) => s.text.trim())).toEqual(["Hei", "der!"]);
  });

  it("reads template text without markup and Jinja code", () => {
    const text = textFromTemplate(`<!DOCTYPE html>{# kommentar! #}<p>{% if a != b %}Hei {{ navn }}{% endif %}</p>`);
    expect(checkText(text)).toEqual([]);
    expect(checkText(textFromTemplate("<p>Hei!</p>"))).toEqual(["exclamation"]);
  });

  it("reads string literals in Jinja code, copy attributes and entities, and keeps line numbers", () => {
    expect(checkText(textFromTemplate('{{ "Hei!" }}'))).toEqual(["exclamation"]);
    expect(checkText(textFromTemplate('{% set t = "fasit" %}'))).toEqual(["fasit"]);
    expect(checkText(textFromTemplate('<img alt="Kasser øl">'))).toEqual(["ol"]);
    expect(checkText(textFromTemplate("<p>Hei&#33;</p>"))).toEqual(["exclamation"]);
    const lines = textFromTemplate("{# en\nto #}\n<p\n class=x>\nHei!</p>").split("\n");
    expect(lines.findIndex((l) => l.includes("Hei!"))).toBe(4);
  });

  it("does not read className, style or literal types as copy", () => {
    const strings = stringsFromSource(
      `type T = "a!"; export default () => <p className="!mt-0" style={{}}>Hei</p>;`,
      "page.tsx",
    );
    expect(strings.map((s) => s.text)).toEqual(["Hei"]);
  });

  // The Landing's content rules (Story 3.13, UX-DR74), for the `landing` section only.
  it.each([
    ["Kundene ser alt.", "landing-customers"],
    ["Pris per student", "landing-prices"],
    ["Bare 990 kr i året", "landing-prices"],
    ["Gratis for alle", "landing-prices"],
    ["Se forsterkningen i kjeden", "landing-amplification"],
    ["«Beste kurs jeg har tatt» – student", "landing-quotes"],
    ["Studentene lærer seg mer", "landing-learning"],
    ["Bedre læring", "landing-learning"],
    ["Studentene forstår kjeden", "landing-learning"],
    ["Uker spilt", "landing-week-counts"],
    ["Spillet varer 36 uker", "landing-week-counts"],
    ["Beer Game på norsk", "beer-game"],
    ["Kasser øl", "ol"],
  ])("fails %j on the Landing (%s)", (text, rule) => {
    expect(checkText(text, { landing: true })).toContain(rule);
  });

  it("passes the Landing's own lines and keeps the rules off other sections", () => {
    for (const text of [
      "Hver uke har en strek og et tall. Studentene ser begge.",
      "Ett sete, Grossist, Uke 4. Veiledet uke.",
      "for klasser på rundt 250 studenter.",
      "Skriv navnet ditt.",
      "Be om lærertilgang",
    ]) {
      expect(checkText(text, { landing: true })).toEqual([]);
    }
    expect(checkText("Pris per student")).toEqual([]);
  });

  it("checks the landing section of nb.ts in a repo", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "copy-check-"));
    const copy = path.join(root, "frontend", "src", "copy");
    fs.mkdirSync(copy, { recursive: true });
    fs.writeFileSync(
      path.join(copy, "nb.ts"),
      `export const nb = { landing: { seat: { a: "36 uker" } }, admin: { b: "36 uker" } };`,
    );
    try {
      expect(checkRepo(root).map((f) => f.rule)).toEqual(["landing-week-counts"]);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  // Story 6.2 (FR-84, AD-19): the briefing, in nb.ts's `games` section, is shown before the
  // Debrief; only the product name «ØL-spillet» is allowed.
  it("holds the briefing to the pre-Debrief rules", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "copy-check-"));
    const copy = path.join(root, "frontend", "src", "copy");
    fs.mkdirSync(copy, { recursive: true });
    fs.writeFileSync(
      path.join(copy, "nb.ts"),
      `export const nb = { games: { briefing: { a: "Som i Beer Game", b: "Bullwhip-effekten", c: "Lykke til!", d: "ØL-spillet" } } };`,
    );
    try {
      expect(checkRepo(root).map((f) => f.rule)).toEqual(["beer-game", "bullwhip", "exclamation"]);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it("lets only the post-reveal `debrief` section of nb.ts name the exercise (Story 9.4)", () => {
    const file = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "copy", "nb.ts");
    const named = stringsFromSource(fs.readFileSync(file, "utf8"), file).filter((s) => /beer[\s-]*game/i.test(s.text));
    expect(named.map((s) => [s.text, s.section])).toEqual([["Øvelsen heter Beer Game.", "debrief"]]);
    // The same string in the pre-reveal Debrief section would fail the check.
    expect(checkText("Øvelsen heter Beer Game.", { preDebrief: true })).toEqual(["beer-game"]);
  });

  it("finds a breach in a mail template and in nb.ts of a repo", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "copy-check-"));
    const tpl = path.join(root, "backend", "app", "platform", "email", "templates");
    const copy = path.join(root, "frontend", "src", "copy");
    fs.mkdirSync(tpl, { recursive: true });
    fs.mkdirSync(copy, { recursive: true });
    fs.writeFileSync(path.join(tpl, "invitation.html"), "<p>Spill Beer Game</p>");
    fs.writeFileSync(path.join(copy, "nb.ts"), `export const nb = { debrief: { a: "bullwhip" }, game: { b: "bullwhip" } };`);
    try {
      const rules = checkRepo(root).map((f) => `${path.basename(f.file)}:${f.rule}`);
      expect(rules).toEqual(["nb.ts:bullwhip", "invitation.html:beer-game"]);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });
});

describe("colour lint", () => {
  it("passes on src/", () => {
    expect(lintRepo()).toEqual([]);
  });

  it.each([
    ['className="bg-[#fff]"', "hex"],
    ["color: #0F2A47;", "hex"],
    ["fill: rgb(0 0 0);", "function"],
    ['style={{ color: "white" }}', "named"],
    ['<rect fill="red" />', "named"],
    ["background-color: black;", "named"],
    ['className="text-[navy]"', "named"],
    ["stroke: oklch(0.5 0.1 200);", "function"],
    ["border: 1px solid red;", "named"],
    ["outline: 2px solid black;", "named"],
    ["box-shadow: 0 0 2px rebeccapurple;", "named"],
    ["color: light-dark(var(--a), var(--b));", "function"],
  ])("fails on %s", (text, id) => {
    expect(lintText(text).map((f) => f.id)).toContain(id);
  });

  it.each([
    'className="bg-ink text-paper"',
    "color: var(--color-ink);",
    'href="#main"',
    "border-color: transparent;",
    'fill="currentColor"',
    "&#160;",
    'href="#add"',
    "this.#cafe = 1;",
    "border: 1px solid var(--color-ink-muted);",
  ])("passes %s", (text) => {
    expect(lintText(text)).toEqual([]);
  });
});
