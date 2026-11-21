// Copy check (AD-19, UX-DR74). It reads every place UI, mail and PDF copy lives:
//   - frontend/src/copy/**/*.ts           the UI copy (nb.ts): string literals via the TypeScript AST
//   - frontend/src/app/print/**/*.{ts,tsx} the print route (Student report PDF): strings and JSX text
//   - backend/app/**/templates/**         the Jinja2 mail and PDF templates: text outside tags and tags' code
// It fails on an exclamation mark, on «øl» outside the product name «ØL-spillet», and on «optimal»
// or «fasit». In copy shown before the Debrief it also fails on «Beer Game» and «bullwhip».
// The Landing's section of nb.ts (`landing`) is also held to the Landing's content rules (Story
// 3.13, UX-DR74): no customers, prices, amplification, quotes, learning claims or week counts.
// Later stories put their copy in these places and add no check of their own.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";

const here = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(here, "..", "..");

/** Top-level sections of `nb` shown only from the Debrief on. */
export const POST_DEBRIEF_SECTIONS = new Set(["debrief", "replay", "individualTest", "studentReport"]);

const NOT_LETTER_BEFORE = "(?<![\\p{L}\\p{N}])";

/** The spine's line under every «Simulert» number (EXPERIENCE.md → Voice), the only «fasit» copy
 * may hold, and only word for word. */
export const SIMULATED_NOTE = "Simulert viser sammenhengen, ikke en fasit.";

export const RULES = [
  { id: "exclamation", message: "utropstegn", pattern: /!/u },
  {
    id: "ol",
    message: "«øl» utenfor produktnavnet «ØL-spillet»",
    pattern: new RegExp(`${NOT_LETTER_BEFORE}øl`, "iu"),
    prepare: (text) => text.replace(/ØL-spillet\p{L}*/gu, ""),
  },
  { id: "optimal", message: "«optimal»", pattern: new RegExp(`${NOT_LETTER_BEFORE}optimal`, "iu") },
  {
    id: "fasit",
    message: "«fasit»",
    pattern: new RegExp(`${NOT_LETTER_BEFORE}fasit`, "iu"),
    // The spine's one line under «Simulert» (EXPERIENCE.md, UX-DR36), word for word, denies the
    // claim; every other «fasit» fails (Story 9.8).
    prepare: (text) => text.replaceAll(SIMULATED_NOTE, ""),
  },
  { id: "beer-game", message: "«Beer Game» før Debriefen", pattern: /beer[\s-]*game/iu, preDebriefOnly: true },
  { id: "bullwhip", message: "«bullwhip» før Debriefen", pattern: /bullwhip/iu, preDebriefOnly: true },
];

/** The Landing's content rules (EXPERIENCE.md → Landing, UX-DR74), for the `landing` section. */
export const LANDING_SECTION = "landing";
const NOT_LETTER_AFTER = "(?![\\p{L}\\p{N}])";
export const LANDING_RULES = [
  { id: "landing-customers", message: "kunder på Landing", pattern: new RegExp(`${NOT_LETTER_BEFORE}kunde`, "iu") },
  {
    id: "landing-prices",
    message: "priser på Landing",
    pattern: new RegExp(`${NOT_LETTER_BEFORE}(?:pris|kr${NOT_LETTER_AFTER}|kroner|gratis)`, "iu"),
  },
  { id: "landing-amplification", message: "forsterkning på Landing", pattern: new RegExp(`${NOT_LETTER_BEFORE}forsterk`, "iu") },
  { id: "landing-quotes", message: "sitater på Landing", pattern: /[«»“”"]/u },
  {
    id: "landing-learning",
    message: "læringspåstander på Landing",
    pattern: new RegExp(`${NOT_LETTER_BEFORE}(?:lærer seg|læring|forstå)`, "iu"),
  },
  {
    id: "landing-week-counts",
    message: "antall uker på Landing",
    pattern: new RegExp(`(?:uker spilt|\\d+\\s*uker${NOT_LETTER_AFTER})`, "iu"),
  },
];

/** Rule ids the text breaks. `landing` adds the Landing's content rules. */
export function checkText(text, { preDebrief = true, landing = false } = {}) {
  return [...RULES, ...(landing ? LANDING_RULES : [])]
    .filter((rule) => preDebrief || !rule.preDebriefOnly)
    .filter((rule) => rule.pattern.test(rule.prepare ? rule.prepare(text) : text))
    .map((rule) => rule.id);
}

function topLevelSection(node) {
  // The outermost property assignment above the node names its section of `nb`.
  let section;
  for (let n = node.parent; n; n = n.parent) {
    if (ts.isPropertyAssignment(n) && n.name && (ts.isIdentifier(n.name) || ts.isStringLiteral(n.name))) {
      section = n.name.text;
    }
  }
  return section;
}

/** Copy strings in a TS/TSX source: string literals, template text and JSX text, with their line. */
export function stringsFromSource(source, fileName = "copy.tsx") {
  const kind = fileName.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(fileName, source, ts.ScriptTarget.Latest, true, kind);
  const out = [];
  const push = (node, text) => {
    if (text.trim() === "") return;
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    out.push({ text, line, section: topLevelSection(node) });
  };
  const visit = (node) => {
    if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) return;
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const parent = node.parent;
      const isKey = parent && ts.isPropertyAssignment(parent) && parent.name === node;
      const isDirective = parent && ts.isExpressionStatement(parent); // "use client"
      const isType = parent && ts.isLiteralTypeNode(parent);
      // className and style are code, not copy (Tailwind's important prefix is a "!").
      const isStyling =
        parent && ts.isJsxAttribute(parent) && ["className", "style"].includes(parent.name.getText(sf));
      if (!isKey && !isDirective && !isType && !isStyling) push(node, node.text);
    } else if (ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node)) {
      push(node, node.text);
    } else if (ts.isJsxText(node)) {
      push(node, node.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return out;
}

const newlines = (m) => "\n".repeat((m.match(/\n/g) ?? []).length);
const quoted = (code) => [...code.matchAll(/"([^"]*)"|'([^']*)'/g)].map((q) => q[1] ?? q[2]).join(" ");
const COPY_ATTRS = /\b(?:alt|title|aria-label|placeholder)\s*=\s*(?:"([^"]*)"|'([^']*)')/gi;

/**
 * The text a Jinja2 template sends: text between tags, string literals inside Jinja code, and the
 * copy attributes (alt, title, aria-label, placeholder). Comments and markup are dropped.
 * Removed spans keep their line breaks, so a finding reports the right line.
 */
export function textFromTemplate(source) {
  return source
    .replace(/\{#[\s\S]*?#\}/g, (m) => ` ${newlines(m)}`)
    .replace(/\{%[\s\S]*?%\}|\{\{[\s\S]*?\}\}/g, (m) => ` ${quoted(m)} ${newlines(m)}`)
    .replace(/<!--[\s\S]*?-->/g, (m) => ` ${newlines(m)}`)
    .replace(/<[^>]*>/g, (m) => {
      const attrs = [...m.matchAll(COPY_ATTRS)].map((a) => a[1] ?? a[2]).join(" ");
      return ` ${attrs} ${newlines(m)}`;
    })
    .replace(/&#33;|&#x21;|&excl;/gi, "!");
}

function walk(dir, accept) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full, accept));
    else if (accept(full)) out.push(full);
  }
  return out;
}

const isTemplateDir = (file) => file.split(path.sep).includes("templates");
const isTest = (file) => /\.test\.[cm]?[jt]sx?$/.test(file);

/** Files the check reads, grouped by how their copy is extracted. */
export function copyFiles(root = REPO_ROOT) {
  return {
    ui: walk(path.join(root, "frontend", "src", "copy"), (f) => /\.tsx?$/.test(f) && !isTest(f)),
    print: walk(path.join(root, "frontend", "src", "app", "print"), (f) => /\.tsx?$/.test(f) && !isTest(f)),
    templates: walk(path.join(root, "backend", "app"), (f) =>
      isTemplateDir(f) && /\.(html|txt|j2|jinja|jinja2)$/.test(f),
    ),
  };
}

/** Every finding in the repo: `{ file, line, rule, text }`. */
export function checkRepo(root = REPO_ROOT) {
  const findings = [];
  const files = copyFiles(root);
  for (const file of files.ui) {
    for (const s of stringsFromSource(fs.readFileSync(file, "utf8"), file)) {
      const preDebrief = !POST_DEBRIEF_SECTIONS.has(s.section);
      const landing = s.section === LANDING_SECTION;
      for (const rule of checkText(s.text, { preDebrief, landing })) findings.push({ file, line: s.line, rule, text: s.text });
    }
  }
  // The print route renders the Student report, which comes after the Debrief.
  for (const file of files.print) {
    for (const s of stringsFromSource(fs.readFileSync(file, "utf8"), file)) {
      for (const rule of checkText(s.text, { preDebrief: false })) findings.push({ file, line: s.line, rule, text: s.text });
    }
  }
  // Mail templates (Invitation, password reset, notices) reach people before the Debrief.
  for (const file of files.templates) {
    const lines = textFromTemplate(fs.readFileSync(file, "utf8")).split("\n");
    lines.forEach((text, i) => {
      for (const rule of checkText(text, { preDebrief: true })) findings.push({ file, line: i + 1, rule, text: text.trim() });
    });
  }
  return findings;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const findings = checkRepo();
  const messages = Object.fromEntries([...RULES, ...LANDING_RULES].map((r) => [r.id, r.message]));
  for (const f of findings) {
    console.error(`${path.relative(REPO_ROOT, f.file)}:${f.line}: ${messages[f.rule]}: ${JSON.stringify(f.text)}`);
  }
  if (findings.length > 0) {
    console.error(`Copy check failed: ${findings.length} finding(s).`);
    process.exit(1);
  }
  const counts = copyFiles();
  console.log(
    `Copy check passed (${counts.ui.length} copy file(s), ${counts.print.length} print file(s), ${counts.templates.length} template(s)).`,
  );
}
