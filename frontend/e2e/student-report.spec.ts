import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

import { type APIResponse, expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, type LiveStudent, orderByApi } from "./support/live-game";

/** Story 13.7 (FR-57, FR-58, NFR-6, NFR-7, AD-8, AD-11, AD-18, UX-DR29) on the local stack: a fresh
 * locked Obligatorisk Class session of one Student, whose Class game of 20 Uker is played to its
 * end through `games.commands` (own Orders, then the Play deadline playout, Story 13.8: the report's
 * game section and its charts). Story 13.10: every later step on the api, so the sample documents
 * them all: the Personal debrief with its Explanation, the line worded by the mock (AI text), the
 * reflection answers and «Fullfør Debriefen»; one quiz attempt, then the dev pass; a Replay played
 * to its end; the Individual test answered and handed in. Before the Testfrist «Rapport» is locked
 * and says what opens it; the dev route passes the Testfrist; «Lag Studentrapport» shows the
 * pending line, and without a reload (the render's `user` event) the Lenke «Last ned
 * Studentrapporten (PDF)» appears within 30 seconds: the real pipeline (snapshot, print route,
 * WeasyPrint `pdf/ua-1` in `worker-batch`, the storage mock). The PDF downloads through the signed
 * URL, and its structure tree marks the AI line (`/UserProperties` `ai_generated`). The proxy
 * refuses the print route and the api's internal snapshot read. Axe and reflow at 320 px and
 * 1440 px. The PDF is kept as the sample CI's veraPDF step checks (`scripts/verapdf`). Story 13.9:
 * «Rapport» states the deletion date, locked and open, and it follows the Testfrist. Story 13.11:
 * the test is assessed on the mock provider; the Bryter «KI-vurdering i rapporten» is off, so the
 * first PDF is the standard one; turned on, a second PDF with the «KI-vurdering» section is made
 * and kept as the second sample (`student-report-ai.pdf`); the standard link still serves the
 * first. What the api refuses is `backend/tests/reports/test_student_report.py` and
 * `test_report_assessment.py`. */
const copy = nb.reports.download;
const CSRF = { "X-Requested-With": "olspillet" };
export const SAMPLE = path.join("test-results", "student-report.pdf");
export const SAMPLE_AI = path.join("test-results", "student-report-ai.pdf");
/** The Student's own Orders for Uke 1 to 16: at least ten after the Guided Uker, so the Debrief
 * has moments to choose. */
const ORDERS = [4, 4, 4, 4, 12, 0, 8, 16, 4, 8, 2, 8, 20, 6, 10, 4];
const EXPLANATION = "Posisjonen er lager − restordre + på vei. Jeg bestilte for mye fordi jeg glemte det som var på vei.";

/** The PDF's objects as text, each deflated stream inflated (pydyf compresses them). */
function pdfText(pdf: Buffer): string {
  const raw = pdf.toString("latin1");
  const parts = [raw];
  for (const match of raw.matchAll(/stream\r?\n([\s\S]*?)\r?\nendstream/g)) {
    try {
      parts.push(zlib.inflateSync(Buffer.from(match[1]!, "latin1")).toString("latin1"));
    } catch {
      // Not a deflated stream: nothing to read.
    }
  }
  return parts.join("\n");
}

async function ok(answer: Promise<APIResponse>, status = 200): Promise<APIResponse> {
  const done = await answer;
  expect(done.status(), await done.text()).toBe(status);
  return done;
}

/** Story 13.10: every step after the game on the api, as the Student takes them. */
async function everyStep(sara: LiveStudent, gameId: string, sessionId: string) {
  const request = sara.context.request;
  // The Personal debrief: the Explanation; the line worded by the mock before step 4 is first read
  // (so it is the line shown and kept); the reflection answers; «Fullfør Debriefen».
  const debrief = await (await ok(request.post(`/api/me/class-sessions/${sessionId}/debrief`, { headers: CSRF }))).json();
  const at = `/api/debriefs/${debrief.id}`;
  await ok(request.post(`${at}/explanation`, { data: { text: EXPLANATION }, headers: CSRF }), 201);
  await ok(request.post(`/api/dev/games/${gameId}/seats/${debrief.role}/narrate?outage=false`, { headers: CSRF }));
  await ok(request.get(`${at}/steps/4`));
  const reflection = await (await ok(request.get(`${at}/reflection`))).json();
  for (const question of reflection.questions as { id: string; kind: string }[]) {
    await ok(request.post(`${at}/reflection/${question.id}`, { data: { text: `Svar om ${question.kind}.` }, headers: CSRF }));
  }
  await ok(request.post(`${at}/finish`, { headers: CSRF }));
  // One quiz attempt with each question's first choice, then the dev pass.
  const quiz = await (await ok(request.get(`${at}/quiz`))).json();
  const answers = (quiz.questions as { id: string; choices: { id: string }[] }[]).map((q) => ({ question_id: q.id, choice_id: q.choices[0]!.id }));
  await ok(request.post(`${at}/quiz/attempts`, { data: { answers }, headers: CSRF }), 201);
  await ok(request.post(`/api/dev/class-sessions/${sessionId}/quiz-passed`, { headers: CSRF }), 204);
  // The Replay: every Uke ordered until it has finished (its length is drawn). Its finish records
  // the `replay` step, without which the test would not open.
  const replay = await (await ok(request.post(`/api/me/class-sessions/${sessionId}/replay`, { headers: CSRF }), 201)).json();
  let week = 1;
  for (; week <= 60; week++) {
    const placed = await request.post(`/api/me/games/${replay.game_id}/weeks/${week}/order`, { data: { order: 4 + (week % 5) }, headers: CSRF });
    if (placed.status() !== 204) {
      // Past its last Uke the Replay takes no Order: refused, not failed.
      expect(placed.status(), await placed.text()).toBe(409);
      break;
    }
  }
  expect(week).toBeGreaterThan(20);
  const finished = await (await ok(request.get(`/api/me/games/${replay.game_id}`))).json();
  expect(finished.status).toBe("finished");
  // The Individual test: opened, every item answered (one Uke of each table left empty), handed in.
  const opened = await (await ok(request.post(`/api/me/class-sessions/${sessionId}/test`, { headers: CSRF }), 201)).json();
  for (const item of opened.items as { id: string; type: string; options: string[]; table: { rows: string[] } | null }[]) {
    const value =
      item.type === "choice"
        ? item.options[0]
        : item.table
          ? item.table.rows.map((_, i) => (i === 1 ? null : 10 + i))
          : item.type === "number"
            ? 16
            : "Forsinkelsen gjorde at ordrene kom for sent.\nDerfor svingte lageret.";
    await ok(request.put(`/api/me/class-sessions/${sessionId}/test/answers/${item.id}`, { data: { value, revision: 1 }, headers: CSRF }));
  }
  await ok(request.post(`/api/me/class-sessions/${sessionId}/test/submit`, { headers: CSRF }));
}

test("a Student makes and downloads the Student report once the Testfrist has passed", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session, a lock and a real PDF render
  const { gameId, sessionId, students } = await liveClassGame(browser, lecturerSession, 1, {
    aiMode: "rule_based",
    debriefMode: "personal",
    obligatory: true,
    width: VIEWPORTS[2]!.width,
    gameSettings: { weeks: 20 },
  });
  const [sara] = students as [(typeof students)[number]];
  try {
    // Story 13.8: the game played to its end, so the sample report holds the game with its charts;
    // Story 13.10: with enough own Orders for the Debrief's moments, then every later step.
    for (const [i, order] of ORDERS.entries()) await orderByApi(sara, gameId, i + 1, order);
    const played = await sara.context.request.post(`/api/dev/games/${gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);
    await everyStep(sara, gameId, sessionId);
    const page = await sara.context.newPage();
    await page.goto("/hjem");
    const stegene = page.locator(`section[aria-labelledby="steps-${sessionId}"]`);
    const report = stegene.locator('li[data-state]').last();
    await expect(report).toContainText(nb.homes.student.locked.report);
    await expect(report).toHaveAttribute("data-state", "locked");
    // Story 13.9: locked or open, «Rapport» states the day the Klasseøkt's data is deleted.
    const deletion = report.locator("[data-deletion-date]");
    await expect(deletion).toHaveText(
      /^Dataene dine fra denne Klasseøkten slettes \d{1,2}\. [a-zø]+ \d{4}\. Last ned Studentrapporten før det\.$/,
    );
    const lockedDay = await deletion.getAttribute("data-deletion-date");
    const early = await sara.context.request.post(`/api/me/class-sessions/${sessionId}/report`, { headers: CSRF });
    expect(early.status()).toBe(409);
    expect((await early.json()).error.code).toBe("report_not_open");

    const passed = await sara.context.request.post(`/api/dev/class-sessions/${sessionId}/test-deadline-passed`, {
      headers: CSRF,
    });
    expect(passed.status()).toBe(200);
    // Story 13.11: the Test-deadline lock and the close of the attempt; `worker-batch` assesses
    // it on the mock provider.
    await ok(sara.context.request.post(`/api/dev/class-sessions/${sessionId}/lock-test`, { headers: CSRF }));
    await ok(sara.context.request.post(`/api/dev/class-sessions/${sessionId}/test/close`, { headers: CSRF }), 204);
    await expect
      .poll(async () => (await (await sara.context.request.get(`/api/me/class-sessions/${sessionId}/test/assessment`)).json()).state, {
        timeout: 30_000,
      })
      .toBe("ready");
    await page.reload();
    // Open; «done» since the AI assessment is ready (Story 12.4 marks the last step so).
    await expect(report).toHaveAttribute("data-state", "done");
    const make = report.getByRole("button", { name: copy.make });
    await expect(make).toBeVisible();
    await expect(report).toContainText(copy.note);
    // Story 13.11: the assessment is ready, so the Bryter is offered, off.
    const bryter = report.getByRole("switch", { name: copy.ai.control });
    await expect(bryter).toHaveAttribute("aria-checked", "false");
    await expect(report).toContainText(copy.ai.help);
    // The Testfrist moved into the past: the deletion date moved with it, in the same save.
    await expect(deletion).toBeVisible();
    expect(await deletion.getAttribute("data-deletion-date")).not.toBe(lockedDay);
    await expectAccessible(page, false);

    const started = Date.now();
    await make.click();
    await expect(report.locator('[data-report-download="pending"]')).toContainText(copy.pending);
    const link = report.getByRole("link", { name: copy.link });
    await expect(link).toBeVisible({ timeout: 30_000 });
    expect(Date.now() - started).toBeLessThan(30_000);
    await expect(page.getByRole("status").filter({ hasText: copy.ready })).toHaveCount(1);
    await expect(report.getByRole("button", { name: copy.again })).toBeVisible();

    // The Lenke goes to the api, which answers a signed URL; the browser saves the PDF.
    const download = page.waitForEvent("download");
    await link.click();
    const saved = await download;
    expect(saved.suggestedFilename()).toBe("studentrapport-klasseokt-1.pdf");
    const file = await saved.path();
    const pdf = fs.readFileSync(file);
    expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
    expect(pdf.length).toBeGreaterThan(5_000);
    fs.mkdirSync(path.dirname(SAMPLE), { recursive: true });
    fs.copyFileSync(file, SAMPLE);
    // Story 13.10: the AI line is marked in the structure tree, for machines (FR-34, UX-DR69).
    const objects = pdfText(pdf);
    expect(objects).toContain("/UserProperties");
    expect(objects).toContain("(ai_generated)");
    const marks = (text: string) => text.split("(ai_generated)").length - 1;

    // Story 13.11: the Bryter on, a report of its own with the «KI-vurdering» section.
    await bryter.click();
    await expect(bryter).toHaveAttribute("aria-checked", "true");
    await expect(report.getByRole("link", { name: copy.link })).toHaveCount(0);
    await report.getByRole("button", { name: copy.make }).click();
    const aiLink = report.getByRole("link", { name: copy.link });
    await expect(aiLink).toBeVisible({ timeout: 30_000 });
    await expect(aiLink).toHaveAttribute("href", /\/report\/file\?ai=true$/);
    const aiDownload = page.waitForEvent("download");
    await aiLink.click();
    const aiPdf = fs.readFileSync(await (await aiDownload).path());
    expect(aiPdf.subarray(0, 5).toString()).toBe("%PDF-");
    fs.copyFileSync(await (await aiDownload).path(), SAMPLE_AI);
    // The AI scores, the feedback and the total are marked too: more marks than the standard one.
    expect(marks(pdfText(aiPdf))).toBeGreaterThan(marks(objects));
    // Off again: the standard link, to the first PDF.
    await bryter.click();
    await expect(report.getByRole("link", { name: copy.link })).toHaveAttribute("href", /\/report\/file$/);

    // The print route and the api's internal snapshot read are refused at the proxy (AD-11).
    for (const internal of ["/print/report/00000000-0000-0000-0000-000000000000?token=x", "/api/internal/report-snapshots/x"]) {
      const answer = await sara.context.request.get(internal);
      expect(answer.status(), internal).toBe(404);
      expect(await answer.text()).not.toContain("student_name");
    }

    await page.setViewportSize({ width: VIEWPORTS[0]!.width, height: VIEWPORTS[0]!.height });
    await expectAccessible(page, true);
    await page.close();
  } finally {
    await sara.context.close();
  }
});
