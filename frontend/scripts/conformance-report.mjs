// The conformance report (Story 15.13, NFR-6). It reads the conformance scan's results (one JSON
// file per viewport, written by `e2e/conformance.spec.ts`), the report's inputs in
// `docs/accessibility/conformance-inputs.json` (the checks tools cannot make, the independent
// review, the surfaces not built yet) and, when given, a veraPDF report; it writes
// `docs/accessibility/conformance-report-<date>.md` and points item R13 of the readiness record
// (`docs/ops/readiness.md`, Story 15.11) at it.
//
//   node scripts/conformance-report.mjs --results <dir> [--verapdf <file>] [--date YYYY-MM-DD] [--out <dir>]
//
// `npm run conformance` (scripts/conformance.mjs) runs the scan first, then this.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(here, "..", "..");
export const ACCESSIBILITY_DIR = path.join(REPO_ROOT, "docs", "accessibility");
export const INPUTS_PATH = path.join(ACCESSIBILITY_DIR, "conformance-inputs.json");
export const READINESS_PATH = path.join(REPO_ROOT, "docs", "ops", "readiness.md");

/** The scan's viewports in report order: id → column heading. */
export const VIEWPORTS = [
  ["320", "320 px"],
  ["360", "360 px"],
  ["1440", "1440 px"],
  ["zoom400", "400 % zoom"],
  ["text200", "200 % text"],
  ["text200-320", "320 px, 200 % text"],
];

const REPORT_NAME = /conformance-report-\d{4}-\d{2}-\d{2}\.md/;

export class ReportError extends Error {}

/** Every `*.json` of the scan's results directory, as one list of surface results. */
export function readResults(dir) {
  if (!fs.existsSync(dir)) throw new ReportError(`no scan results: ${dir} does not exist (run the scan first)`);
  const files = fs.readdirSync(dir).filter((name) => name.endsWith(".json"));
  if (files.length === 0) throw new ReportError(`no scan results: ${dir} holds no .json file (run the scan first)`);
  const results = files.flatMap((name) => {
    try {
      return JSON.parse(fs.readFileSync(path.join(dir, name), "utf8")).results ?? [];
    } catch (error) {
      throw new ReportError(`${name} in ${dir} is not a scan result: ${error.message}`);
    }
  });
  if (results.length === 0) throw new ReportError(`no scan results: the files in ${dir} hold no surface`);
  return results;
}

/** The veraPDF summary of a report file (its XML or text output): compliant or not, with counts. */
export function readVeraPdf(file) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch (error) {
    throw new ReportError(`cannot read the veraPDF result ${file}: ${error.message}`);
  }
  const batch = text.match(/<validationReports\b[^>]*>/);
  if (batch) {
    const count = (name) => Number(batch[0].match(new RegExp(`\\b${name}="(\\d+)"`))?.[1] ?? 0);
    const [compliant, nonCompliant, failed] = [count("compliant"), count("nonCompliant"), count("failedJobs")];
    return {
      file,
      // A PDF veraPDF could not process counts against the result.
      compliant: compliant > 0 && nonCompliant === 0 && failed === 0,
      detail: `${compliant} compliant, ${nonCompliant} non-compliant${failed > 0 ? `, ${failed} not processed` : ""}`,
    };
  }
  const single = [...text.matchAll(/isCompliant="(true|false)"/g)].map((m) => m[1] === "true");
  if (single.length > 0) {
    const failed = single.filter((ok) => !ok).length;
    return { file, compliant: failed === 0, detail: `${single.length - failed} compliant, ${failed} non-compliant` };
  }
  throw new ReportError(`${file} is not a veraPDF report (no compliant/isCompliant attribute)`);
}

/** One cell of the surface table: `pass`, the rule ids, `horizontal scroll`, or `not checked`. */
export function cell(result) {
  if (!result || result.error) return "not checked";
  const parts = result.violations.map((v) => v.id);
  if (result.scrolls) parts.push("horizontal scroll");
  return parts.length === 0 ? "pass" : parts.join(", ");
}

/** A manual check is done when it says who did it and when. */
export function checkStatus(check) {
  return check.by && check.date ? "done" : "open";
}

/** Text for a table cell or a code span: no pipe, newline or backtick breaks the Markdown. */
const md = (text) => String(text ?? "").replaceAll("|", "\\|").replaceAll("\n", " ").replaceAll("`", "'");

/** The report's Markdown. Pure: every input is passed in. */
export function renderReport({ results, inputs, verapdf, date, commit }) {
  const surfaces = [];
  const seen = new Map();
  for (const r of results) {
    const key = `${r.role}\u0000${r.surface}`;
    if (!seen.has(key)) {
      seen.set(key, { role: r.role, surface: r.surface, pattern: r.pattern ?? r.path, byViewport: new Map() });
      surfaces.push(seen.get(key));
    }
    seen.get(key).byViewport.set(r.viewport, r);
  }
  const cells = surfaces.flatMap((s) => VIEWPORTS.map(([id]) => cell(s.byViewport.get(id))));
  const passed = cells.filter((c) => c === "pass").length;
  const unchecked = cells.filter((c) => c === "not checked").length;
  const failing = cells.length - passed - unchecked;
  const missing = VIEWPORTS.filter(([id]) => !results.some((r) => r.viewport === id)).map(([, label]) => label);
  const checks = inputs.manualChecks ?? [];
  const open = checks.filter((c) => checkStatus(c) === "open").length;

  const lines = [];
  lines.push(`# Conformance report, ${date}`);
  lines.push("");
  lines.push(
    "ØL-spillet, the web app. Standard: WCAG 2.1, levels A and AA (NFR-6). Generated by `npm run conformance` in `frontend/` (Story 15.13); do not edit by hand, change `docs/accessibility/conformance-inputs.json` and run the command again.",
  );
  lines.push("");
  lines.push(`- Build: ${commit}.`);
  lines.push(
    "- Automated: Playwright (Chromium) with axe-core, tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, on the local stack with fresh data, and the check that the page does not scroll sideways. 400 % zoom is a 320 × 256 CSS-pixel viewport (1280 × 1024 at 400 %); 200 % text doubles the root font size (`html { font-size: 200% }`, as the product's own specs do; the app sizes its text in rem), at 1280 and at 320 px.",
  );
  lines.push(
    `- Result: ${surfaces.length} surfaces × ${VIEWPORTS.length} viewports = ${cells.length} checks: ${passed} pass, ${failing} with violations, ${unchecked} not checked.`,
  );
  if (missing.length > 0) lines.push(`- No results at all for: ${missing.join(", ")} (the scan did not finish there).`);
  lines.push(`- Checks tools cannot make: ${checks.length - open} of ${checks.length} done, ${open} open.`);
  lines.push("");
  lines.push("## Surfaces");
  lines.push("");
  lines.push(
    "`pass` means axe found no violation and the page did not scroll sideways. Tools test only part of WCAG 2.1; the rest is in the checks tools cannot make, below. Each surface is scanned in the state the fresh data gives it:",
  );
  lines.push("");
  for (const limit of inputs.scanLimits ?? []) lines.push(`- ${limit}`);
  lines.push("");
  lines.push(`| Role | Surface | Address | ${VIEWPORTS.map(([, label]) => label).join(" | ")} |`);
  lines.push(`| --- | --- | --- | ${VIEWPORTS.map(() => "---").join(" | ")} |`);
  for (const s of surfaces) {
    lines.push(
      `| ${md(s.role)} | ${md(s.surface)} | \`${md(s.pattern)}\` | ${VIEWPORTS.map(([id]) => md(cell(s.byViewport.get(id)))).join(" | ")} |`,
    );
  }
  lines.push("");

  const problems = results.filter((r) => r.error || r.scrolls || r.violations.length > 0);
  lines.push("## Violations found");
  lines.push("");
  if (problems.length === 0 && unchecked === 0) {
    lines.push("None: axe found no violation and no page scrolled sideways, on any surface at any viewport.");
  } else if (problems.length === 0) {
    lines.push(`None on the ${cells.length - unchecked} checks that ran; ${unchecked} were not checked.`);
  } else {
    for (const r of problems) {
      const label = VIEWPORTS.find(([id]) => id === r.viewport)?.[1] ?? r.viewport;
      lines.push(`### ${r.role}, ${r.surface}, ${label}`);
      lines.push("");
      if (r.error) lines.push(`- Not checked: the page did not open (${md(r.error)}).`);
      if (r.scrolls) lines.push("- The page scrolls sideways (WCAG 1.4.10 Reflow).");
      for (const v of r.violations) {
        lines.push(`- \`${v.id}\` (${v.impact ?? "impact unknown"}): ${md(v.help)}. Elements: ${v.targets.map((t) => `\`${md(t)}\``).join(", ")}.`);
      }
      lines.push("");
    }
  }
  lines.push("");

  lines.push("## Student report PDF (veraPDF)");
  lines.push("");
  if (verapdf) {
    lines.push(`${verapdf.compliant ? "Compliant" : "Not compliant"} with PDF/UA: ${verapdf.detail} (\`${md(path.basename(verapdf.file))}\`).`);
  } else {
    lines.push(
      "Not run: no Student report PDF exists on this build (Epic 13 adds it). Run the command again with `--verapdf <report>` once CI checks a sample report (SETUP-GUIDE §7).",
    );
  }
  lines.push("");

  lines.push("## Not built yet");
  lines.push("");
  lines.push("These surfaces are not in this build and were not checked. The report must be made again when they are.");
  lines.push("");
  for (const item of inputs.notYetBuilt ?? []) lines.push(`- ${item}`);
  lines.push("");

  lines.push("## Checks tools cannot make (the founder's)");
  lines.push("");
  lines.push("Each stays open until the founder records who did it and when, in `docs/accessibility/conformance-inputs.json`.");
  lines.push("");
  lines.push("| Check | Owner | Done by | Date | Result | Status |");
  lines.push("| --- | --- | --- | --- | --- | --- |");
  for (const c of checks) {
    lines.push(
      `| ${md(c.check)} | ${md(c.owner ?? "founder")} | ${md(c.by ?? "")} | ${md(c.date ?? "")} | ${md(c.result ?? "")} | ${checkStatus(c)} |`,
    );
  }
  lines.push("");

  const review = inputs.independentReview;
  if (review) {
    lines.push("## Independent review in the founder's place");
    lines.push("");
    lines.push(
      `${md(review.by)}, ${md(review.date)}, with ${md(review.tool)}. The build ran with no human in the loop, so an independent review agent did the keyboard, focus and axe checks the founder would have made. It does not close any check above: an agent cannot use a screen reader.`,
    );
    lines.push("");
    lines.push(review.summary);
    lines.push("");
    if ((review.observations ?? []).length > 0) {
      lines.push("Observations (none is a WCAG 2.1 A/AA failure):");
      lines.push("");
      for (const o of review.observations) lines.push(`- ${o}`);
      lines.push("");
    }
    if ((review.notChecked ?? []).length > 0) {
      lines.push("Not checked by the review:");
      lines.push("");
      for (const o of review.notChecked) lines.push(`- ${o}`);
      lines.push("");
    }
  }
  return `${lines.join("\n").replace(/\n{3,}/g, "\n\n").trimEnd()}\n`;
}

/** The readiness record with R13's link pointing at `reportName`. */
export function updateReadiness(text, reportName) {
  const lines = text.split("\n");
  const index = lines.findIndex((line) => line.startsWith("| R13 |"));
  if (index < 0) throw new ReportError("the readiness record has no R13 row");
  if (!REPORT_NAME.test(lines[index])) throw new ReportError("the readiness record's R13 row names no conformance report");
  lines[index] = lines[index].replace(new RegExp(REPORT_NAME.source, "g"), reportName);
  return lines.join("\n");
}

function today() {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Oslo" }).format(new Date());
}

/** The commit the scan ran on, and whether the working tree held changes on top of it. */
function headCommit() {
  try {
    const head = execFileSync("git", ["rev-parse", "HEAD"], { cwd: REPO_ROOT, encoding: "utf8" }).trim();
    const dirty = execFileSync("git", ["status", "--porcelain"], { cwd: REPO_ROOT, encoding: "utf8" }).trim();
    return `commit \`${head}\`${dirty ? ", with uncommitted changes that the commit adding this report holds" : ""}`;
  } catch {
    return "unknown";
  }
}

/** The value after `--name`; a flag given without one is refused, not ignored. */
export function argument(argv, name) {
  const index = argv.indexOf(name);
  if (index < 0) return undefined;
  const value = argv[index + 1];
  if (value === undefined || value.startsWith("--")) throw new ReportError(`${name} needs a value`);
  return value;
}

export function main(argv = process.argv.slice(2)) {
  const resultsDir = argument(argv, "--results") ?? path.join(here, "..", "test-results", "conformance");
  const date = argument(argv, "--date") ?? today();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new ReportError(`--date must be YYYY-MM-DD, not ${date}`);
  const verapdfFile = argument(argv, "--verapdf");
  const results = readResults(resultsDir);
  const verapdf = verapdfFile ? readVeraPdf(verapdfFile) : null;
  const inputs = JSON.parse(fs.readFileSync(INPUTS_PATH, "utf8"));
  const reportName = `conformance-report-${date}.md`;
  const report = renderReport({ results, inputs, verapdf, date, commit: headCommit() });
  // `--out <dir>`: a trial report elsewhere, which leaves the readiness record as it is.
  const out = argument(argv, "--out");
  if (out) {
    fs.mkdirSync(out, { recursive: true });
    fs.writeFileSync(path.join(out, reportName), report);
    console.log(`Wrote ${path.join(out, reportName)}; the readiness record is unchanged.`);
    return;
  }
  const readiness = updateReadiness(fs.readFileSync(READINESS_PATH, "utf8"), reportName);
  fs.writeFileSync(path.join(ACCESSIBILITY_DIR, reportName), report);
  fs.writeFileSync(READINESS_PATH, readiness);
  console.log(`Wrote docs/accessibility/${reportName}; R13 of docs/ops/readiness.md names it.`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    if (!(error instanceof ReportError)) throw error;
    console.error(`conformance report: ${error.message}`);
    process.exit(1);
  }
}
