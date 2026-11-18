// Colour lint (UX-DR1, AD-18): fails the web build (`prebuild`) on a literal colour anywhere in
// src/ outside the theme folder src/theme/. Colours come from the theme tokens only:
// Tailwind classes such as `text-ink`, or `var(--color-ink)` in CSS and hand-made SVG.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const SRC = path.resolve(here, "..", "src");
export const THEME_DIR = path.join(SRC, "theme");

// The 148 CSS named colours.
const NAMED = [
  "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque", "black",
  "blanchedalmond", "blue", "blueviolet", "brown", "burlywood", "cadetblue", "chartreuse",
  "chocolate", "coral", "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
  "darkgoldenrod", "darkgray", "darkgreen", "darkgrey", "darkkhaki", "darkmagenta",
  "darkolivegreen", "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen",
  "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise", "darkviolet", "deeppink",
  "deepskyblue", "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite", "forestgreen",
  "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "green", "greenyellow",
  "grey", "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender",
  "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
  "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey", "lightpink", "lightsalmon",
  "lightseagreen", "lightskyblue", "lightslategray", "lightslategrey", "lightsteelblue",
  "lightyellow", "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine",
  "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue",
  "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue", "mintcream",
  "mistyrose", "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange",
  "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise", "palevioletred",
  "papayawhip", "peachpuff", "peru", "pink", "plum", "powderblue", "purple", "rebeccapurple",
  "red", "rosybrown", "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell",
  "sienna", "silver", "skyblue", "slateblue", "slategray", "slategrey", "snow", "springgreen",
  "steelblue", "tan", "teal", "thistle", "tomato", "turquoise", "violet", "wheat", "white",
  "whitesmoke", "yellow", "yellowgreen",
];
const NAMED_ALT = NAMED.join("|");

export const PATTERNS = [
  // Not after `&` (entities), `.` (private fields), `href="` or `url(` (fragment links).
  {
    id: "hex",
    pattern: /(?<![\w&.]|href=["']|url\()#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![\w-])/gi,
  },
  {
    id: "function",
    pattern: /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color-mix|color|light-dark)\(/gi,
  },
  // A named colour in a colour-bearing CSS property (shorthands included), an inline-style value,
  // an SVG paint attribute or a Tailwind arbitrary value.
  {
    id: "named",
    pattern: new RegExp(
      `(?:(?:color|background(?:-color)?|fill|stroke|stop-color|caret-color|accent-color|box-shadow|text-shadow|text-decoration(?:-color)?|outline(?:-color)?|column-rule(?:-color)?|border(?:-(?:top|right|bottom|left|block|inline)(?:-start|-end)?)?(?:-color)?)\\s*[:=]\\s*["'{]?\\s*["']?(?:[^;"'{}\\n]*\\s)?|\\[)(?:${NAMED_ALT})\\b`,
      "gi",
    ),
  },
];

/** Findings `{ id, line, match }` in one file's text. */
export function lintText(text) {
  const findings = [];
  const lines = text.split("\n");
  lines.forEach((line, i) => {
    for (const { id, pattern } of PATTERNS) {
      for (const m of line.matchAll(pattern)) findings.push({ id, line: i + 1, match: m[0] });
    }
  });
  return findings;
}

export function lintFiles(dir = SRC) {
  const out = [];
  const walk = (d) => {
    for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
      const full = path.join(d, entry.name);
      if (entry.isDirectory()) {
        if (full !== THEME_DIR) walk(full);
      } else if (/\.(?:css|[cm]?[jt]sx?|svg)$/.test(entry.name) && !/\.test\.[cm]?[jt]sx?$/.test(entry.name)) {
        out.push(full);
      }
    }
  };
  walk(dir);
  return out;
}

export function lintRepo(dir = SRC) {
  return lintFiles(dir).flatMap((file) =>
    lintText(fs.readFileSync(file, "utf8")).map((f) => ({ file, ...f })),
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const findings = lintRepo();
  for (const f of findings) {
    console.error(`${path.relative(process.cwd(), f.file)}:${f.line}: literal colour ${f.match} (use a theme token)`);
  }
  if (findings.length > 0) {
    console.error(`Colour lint failed: ${findings.length} literal colour(s) outside src/theme/.`);
    process.exit(1);
  }
  console.log(`Colour lint passed (${lintFiles().length} file(s)).`);
}
