import fs from "node:fs";
import path from "node:path";

import { type APIResponse, expect, type Page, test } from "@playwright/test";

import { nb } from "../../src/copy/nb";
import { freshClass, freshLecturer } from "../support/classes";

/**
 * UJ-9's comparison (PRD §2.3): one fresh Lecturer with two finished Class sessions of the same
 * Class, last year's and this year's, each of 10 registered Students (the anonymisation threshold
 * of Tverrklasse-statistikk, FR-65). The two years are set up through the api, as the other journeys
 * did through the UI: Students registered by hand, the allocation drawn and confirmed, the Class
 * games started by the Lecturer and played out by AI players at the Play deadline (the local dev
 * `playout`), the Test deadline passed and locked (dev routes). The sweep in `worker-batch` then
 * writes each Class session's aggregate, as it does after every Test deadline. What the Lecturer
 * reads is checked in the UI: the comparison with both Class sessions, a filter that changes the
 * count, and «Fjoråret» on the Klasserapport's Kostnadsfordeling.
 */
test.describe.configure({ mode: "serial" });

const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const SHOTS = path.join(__dirname, "..", "..", "..", ".docs", "implementation-artifacts", "screenshots", "journeys");
const STUDENTS = 10;

async function ok(response: APIResponse, what: string): Promise<APIResponse> {
  expect(response.ok(), `${what}: ${response.status()} ${await response.text()}`).toBe(true);
  return response;
}

/** One year's Class session, played out and past its Test deadline. */
async function finishedYear(lecturer: Page, classId: string, aiMode: "llm" | "rule_based"): Promise<string> {
  const created = await ok(await lecturer.request.post(`/api/classes/${classId}/class-sessions`, { headers: CSRF }), "create");
  const sessionId = ((await created.json()) as { id: string }).id;
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  await ok(
    await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
      data: { ai_mode: aiMode, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
      headers: CSRF,
    }),
    "save",
  );
  const drawn = (await (await ok(await lecturer.request.post(`/api/class-sessions/${sessionId}/allocation`, { headers: CSRF }), "draw")).json()) as {
    draft: { id: string; revision: number };
  };
  await ok(
    await lecturer.request.post(`/api/class-sessions/${sessionId}/allocation/confirm`, {
      data: { draft_id: drawn.draft.id, revision: drawn.draft.revision },
      headers: CSRF,
    }),
    "confirm",
  );
  await ok(await lecturer.request.post(`/api/dev/class-sessions/${sessionId}/lock`, { headers: CSRF }), "lock");
  const games = (await (await lecturer.request.get(`/api/class-sessions/${sessionId}/start-games`)).json()).games as { game_id: string }[];
  expect(games.length).toBe(3);
  const ids = games.map((g) => g.game_id);
  await ok(await lecturer.request.post(`/api/class-sessions/${sessionId}/start-games`, { data: { game_ids: ids }, headers: CSRF }), "start");
  for (const id of ids) await ok(await lecturer.request.post(`/api/dev/games/${id}/playout`, { headers: CSRF, timeout: 120_000 }), "playout");
  await ok(await lecturer.request.post(`/api/dev/class-sessions/${sessionId}/test-deadline-passed`, { headers: CSRF }), "deadline");
  await ok(await lecturer.request.post(`/api/dev/class-sessions/${sessionId}/lock-test`, { headers: CSRF }), "lock-test");
  return sessionId;
}

test("UJ-9: Tverrklasse-statistikk compares last year's and this year's Class session, filters, and the Klasserapport shows «Fjoråret»", async ({
  page,
  browser,
}) => {
  test.setTimeout(15 * 60_000);
  const lecturer = await freshLecturer(page, browser);
  await lecturer.setViewportSize({ width: 1440, height: 900 });
  const klass = await freshClass(lecturer);
  const tag = `${Date.now() % 1_000_000}`;
  for (let i = 0; i < STUDENTS; i++) {
    await ok(
      await lecturer.request.post(`/api/classes/${klass.id}/roster/manual`, {
        data: { email: `tverr-${tag}-${i}@stud.example.no`, name: `Student${i + 1} ${tag}` },
        headers: CSRF,
      }),
      "register",
    );
  }
  // Last year with rule-based players, this year with LLM players: the AI-mode filter tells them apart.
  const lastYear = await finishedYear(lecturer, klass.id, "rule_based");
  const thisYear = await finishedYear(lecturer, klass.id, "llm");

  // The sweep writes both aggregates once the Test deadlines have passed.
  const copy = nb.crossClass;
  const rows = lecturer.locator("[data-compare-bars=chain-median] [data-compare-row]");
  await expect(async () => {
    await lecturer.goto("/tverrklasse-statistikk");
    await expect(rows).toHaveCount(2, { timeout: 3_000 });
  }).toPass({ timeout: 4 * 60_000, intervals: [10_000] });
  await expect(lecturer.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
  await expect(rows.nth(0)).toContainText(copy.session(klass.name, 1));
  await expect(rows.nth(1)).toContainText(copy.session(klass.name, 2));
  await expect(lecturer.getByText(copy.empty)).toHaveCount(0);
  fs.mkdirSync(SHOTS, { recursive: true });
  await lecturer.screenshot({ path: path.join(SHOTS, "uj-9-cross-class-compared.png"), fullPage: true });

  // A filter changes the count: LLM players only leaves one Class session, and no bars to compare;
  // «Alle» brings both back.
  const group = lecturer.locator("[data-filter-group=ai_mode]");
  await expect(group.getByRole("button", { name: copy.all })).toHaveText(`${copy.all}2`);
  await expect(group.getByRole("button", { name: copy.aiModes.llm })).toHaveText(`${copy.aiModes.llm}1`);
  await group.getByRole("button", { name: copy.aiModes.llm }).click();
  await expect(group.getByRole("button", { name: copy.aiModes.llm })).toHaveAttribute("aria-pressed", "true");
  await expect(lecturer.locator("[data-cross-class-announce]")).toHaveText(copy.comparing(1, 2));
  await expect(rows).toHaveCount(0);
  await lecturer.screenshot({ path: path.join(SHOTS, "uj-9-cross-class-filtered.png"), fullPage: true });
  await group.getByRole("button", { name: copy.all }).click();
  await expect(rows).toHaveCount(2);

  // This year's Klasserapport marks last year's median on the Kostnadsfordeling.
  const chain = lecturer.locator("[data-report-section=chain]");
  // The report's per-game figures are stored by their own jobs a moment after the playout.
  await expect(async () => {
    await lecturer.goto(`/klasseokter/${thisYear}/klasserapport`);
    await expect(chain.locator("[data-chain-summary]")).toContainText("Fjoråret ", { timeout: 3_000 });
  }).toPass({ timeout: 3 * 60_000, intervals: [10_000] });
  await expect(chain.locator("svg [data-mark=previous] text")).toHaveText(/^Fjoråret \d/);
  await lecturer.screenshot({ path: path.join(SHOTS, "uj-9-class-report-fjoraret.png"), fullPage: true });
  await lecturer.goto(`/klasseokter/${lastYear}/klasserapport`);
  await expect(lecturer.locator("[data-report-section=chain] [data-chain-summary]")).not.toContainText("Fjoråret");
});
