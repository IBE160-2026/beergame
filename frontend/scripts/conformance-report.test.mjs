import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  argument,
  cell,
  checkStatus,
  INPUTS_PATH,
  READINESS_PATH,
  readResults,
  readVeraPdf,
  renderReport,
  ReportError,
  updateReadiness,
  VIEWPORTS,
} from "./conformance-report.mjs";

/** The conformance report (Story 15.13): one test per row of the spec's I/O matrix. */
const result = (over = {}) => ({
  surface: "Hjem",
  role: "Student",
  pattern: "/hjem",
  path: "/hjem",
  viewport: "320",
  violations: [],
  scrolls: false,
  error: null,
  ...over,
});
const VIOLATION = { id: "color-contrast", impact: "serious", help: "Elements must meet minimum color contrast ratio thresholds", targets: ["main p"] };
const INPUTS = {
  manualChecks: [
    { check: "Screen reader", owner: "founder", by: null, date: null, result: null },
    { check: "Keyboard only", owner: "founder", by: "Kari", date: "2026-12-01", result: "pass" },
  ],
  notYetBuilt: ["Individual test (Epic 11)."],
};

function tmp(name, text) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "conformance-"));
  if (name) fs.writeFileSync(path.join(dir, name), text);
  return dir;
}

function report(results, verapdf = null) {
  return renderReport({ results, inputs: INPUTS, verapdf, date: "2026-11-22", commit: "abc" });
}

/** The table row of `surface`, split into its cells. */
function row(text, surface) {
  const line = text.split("\n").find((l) => l.startsWith(`| Student | ${surface} |`));
  return line.split(" | ").map((c) => c.replace(/^\| |\s\|$/g, ""));
}

describe("conformance report", () => {
  it("a clean surface reads pass", () => {
    expect(cell(result())).toBe("pass");
  });

  it("violations list the rule ids in the cell and the details below", () => {
    const text = report([result({ violations: [VIOLATION] })]);
    expect(row(text, "Hjem")[3]).toBe("color-contrast");
    expect(text).toContain("### Student, Hjem, 320 px");
    expect(text).toContain("`color-contrast` (serious): Elements must meet minimum color contrast ratio thresholds. Elements: `main p`.");
  });

  it("a page that scrolls sideways says so, with any rule ids", () => {
    expect(cell(result({ scrolls: true }))).toBe("horizontal scroll");
    expect(cell(result({ scrolls: true, violations: [VIOLATION] }))).toBe("color-contrast, horizontal scroll");
  });

  it("a surface that did not open reads not checked, with the error's first line", () => {
    const text = report([result({ error: "Timeout 15000ms exceeded." })]);
    expect(row(text, "Hjem")[3]).toBe("not checked");
    expect(text).toContain("Not checked: the page did not open (Timeout 15000ms exceeded.).");
  });

  it("a viewport with no result reads not checked, and the summary names it", () => {
    const text = report([result()]);
    const cells = row(text, "Hjem");
    expect(cells.slice(3)).toEqual(["pass", ...VIEWPORTS.slice(1).map(() => "not checked")]);
    expect(text).toContain(`- No results at all for: ${VIEWPORTS.slice(1).map(([, label]) => label).join(", ")}`);
    expect(text).toContain(`None on the 1 checks that ran; ${VIEWPORTS.length - 1} were not checked.`);
    expect(text).not.toContain("on any surface at any viewport");
  });

  it("without veraPDF the report says why it was not run", () => {
    expect(report([result()])).toContain("Not run: no Student report PDF exists on this build (Epic 13 adds it).");
  });

  it("reads a veraPDF report and states its result", () => {
    const xml = '<report><batchSummary><validationReports compliant="1" nonCompliant="0" failedJobs="0">1</validationReports></batchSummary></report>';
    const file = path.join(tmp("r.xml", xml), "r.xml");
    const verapdf = readVeraPdf(file);
    expect(verapdf.compliant).toBe(true);
    expect(report([result()], verapdf)).toContain("Compliant with PDF/UA: 1 compliant, 0 non-compliant (`r.xml`).");
    const failing = path.join(tmp("f.xml", '<validationReport isCompliant="false"/>'), "f.xml");
    expect(readVeraPdf(failing).compliant).toBe(false);
    // A PDF veraPDF could not process is not a pass.
    const unprocessed = '<validationReports failedJobs="1" compliant="1" nonCompliant="0">2</validationReports>';
    const broken = readVeraPdf(path.join(tmp("b.xml", unprocessed), "b.xml"));
    expect(broken).toMatchObject({ compliant: false, detail: "1 compliant, 0 non-compliant, 1 not processed" });
  });

  it("refuses a veraPDF file it cannot read or understand", () => {
    expect(() => readVeraPdf(path.join(os.tmpdir(), "no-such-verapdf.xml"))).toThrow(ReportError);
    expect(() => readVeraPdf(path.join(tmp("x.txt", "hello"), "x.txt"))).toThrow(/not a veraPDF report/);
  });

  it("a manual check is open until it says who and when, then done", () => {
    expect(checkStatus(INPUTS.manualChecks[0])).toBe("open");
    expect(checkStatus({ ...INPUTS.manualChecks[0], by: "Kari" })).toBe("open");
    expect(checkStatus(INPUTS.manualChecks[1])).toBe("done");
    const text = report([result()]);
    expect(text).toContain("| Screen reader | founder |  |  |  | open |");
    expect(text).toContain("| Keyboard only | founder | Kari | 2026-12-01 | pass | done |");
    expect(text).toContain("Checks tools cannot make: 1 of 2 done, 1 open.");
  });

  it("refuses to report without results", () => {
    expect(() => readResults(path.join(os.tmpdir(), "no-such-conformance-dir"))).toThrow(/does not exist/);
    expect(() => readResults(tmp())).toThrow(/holds no .json file/);
    expect(() => readResults(tmp("320.json", JSON.stringify({ results: [] })))).toThrow(/hold no surface/);
    expect(() => readResults(tmp("320.json", '{"results": ['))).toThrow(ReportError);
    const dir = tmp("320.json", JSON.stringify({ results: [result()] }));
    expect(readResults(dir)).toHaveLength(1);
  });

  it("points R13 of the readiness record at the new report, and refuses without the row", () => {
    const record = "| R12 | x |\n| R13 | Conformance report [conformance-report-2026-11-22.md](../accessibility/conformance-report-2026-11-22.md) | founder |\n";
    expect(updateReadiness(record, "conformance-report-2027-01-05.md")).toBe(
      "| R12 | x |\n| R13 | Conformance report [conformance-report-2027-01-05.md](../accessibility/conformance-report-2027-01-05.md) | founder |\n",
    );
    expect(() => updateReadiness("| R12 | x |\n", "conformance-report-2027-01-05.md")).toThrow(/no R13 row/);
    expect(() => updateReadiness("| R13 | nothing |\n", "conformance-report-2027-01-05.md")).toThrow(/names no conformance report/);
  });

  it("a flag without its value is refused", () => {
    expect(argument(["--date", "2026-11-22"], "--date")).toBe("2026-11-22");
    expect(argument([], "--date")).toBeUndefined();
    expect(() => argument(["--verapdf"], "--verapdf")).toThrow(/needs a value/);
    expect(() => argument(["--from", "--verapdf", "x"], "--from")).toThrow(/needs a value/);
  });

  it("a selector with a backtick does not break the Markdown", () => {
    const text = report([result({ violations: [{ ...VIOLATION, targets: ["a[title=`x`]"] }] })]);
    expect(text).toContain("Elements: `a[title='x']`.");
  });

  it("the repository's inputs, readiness record and committed report agree", () => {
    const inputs = JSON.parse(fs.readFileSync(INPUTS_PATH, "utf8"));
    expect(inputs.manualChecks.length).toBeGreaterThan(0);
    const named = fs.readFileSync(READINESS_PATH, "utf8").match(/\| R13 \|[^\n]*?(conformance-report-\d{4}-\d{2}-\d{2}\.md)/)[1];
    const committed = fs.readFileSync(path.join(path.dirname(INPUTS_PATH), named), "utf8");
    // The committed report is the generator's: every viewport a column, every check counted.
    expect(committed).toContain(`| Role | Surface | Address | ${VIEWPORTS.map(([, label]) => label).join(" | ")} |`);
    expect(committed).toMatch(new RegExp(`× ${VIEWPORTS.length} viewports`));
  });
});
