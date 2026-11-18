import fs from "node:fs";
import os from "node:os";
import path from "node:path";

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
