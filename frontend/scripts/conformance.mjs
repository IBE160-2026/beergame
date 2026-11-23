// `npm run conformance` (Story 15.13): run the conformance scan against the stack at
// `E2E_BASE_URL` (default the local compose stack), then write the dated report.
//
//   npm run conformance                         scan, then report
//   npm run conformance -- --from <dir>         report from results already made (a CI artifact)
//   npm run conformance -- --verapdf <file>     also state the veraPDF result of a sample report
//
// The scan records violations instead of failing on them, so its exit code is not the report's: a
// scan that could not run leaves no results, and the report then refuses.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { argument, main, ReportError } from "./conformance-report.mjs";

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const fromIndex = argv.indexOf("--from");
const rest = fromIndex >= 0 ? argv.filter((_, i) => i !== fromIndex && i !== fromIndex + 1) : argv;

try {
  const from = argument(argv, "--from");
  const results = from ? path.resolve(from) : path.join(frontend, "test-results", "conformance");
  if (!from) {
    // A fresh scan: no result of an earlier run may stand in for a viewport this run did not reach.
    fs.rmSync(results, { recursive: true, force: true });
    const cli = path.join(frontend, "node_modules", "@playwright", "test", "cli.js");
    const scan = spawnSync(process.execPath, [cli, "test", "e2e/conformance.spec.ts", "--workers=4"], {
      cwd: frontend,
      stdio: "inherit",
      env: { ...process.env, CONFORMANCE: "1", CONFORMANCE_OUT: results },
    });
    if (scan.error) throw new ReportError(`the scan did not start: ${scan.error.message}`);
  }
  main(["--results", results, ...rest]);
} catch (error) {
  if (!(error instanceof ReportError)) throw error;
  console.error(`conformance report: ${error.message}`);
  process.exit(1);
}
