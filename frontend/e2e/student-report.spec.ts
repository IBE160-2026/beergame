import fs from "node:fs";
import path from "node:path";

import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, test, VIEWPORTS } from "./support/classes";
import { liveClassGame, orderByApi } from "./support/live-game";

/** Story 13.7 (FR-57, FR-58, NFR-6, NFR-7, AD-8, AD-11, AD-18, UX-DR29) on the local stack: a fresh
 * locked Obligatorisk Class session of one Student, whose Class game of 20 Uker is played to its
 * end through `games.commands` (an Order, then the Play deadline playout, Story 13.8: the report's
 * game section and its charts), with steps recorded through the dev route up to the Replay. Before the Testfrist «Rapport» is locked and says what opens it; the dev route
 * passes the Testfrist; «Lag Studentrapport» shows the pending line, and without a reload (the
 * render's `user` event) the Lenke «Last ned Studentrapporten (PDF)» appears within 30 seconds:
 * the real pipeline (snapshot, print route, WeasyPrint `pdf/ua-1` in `worker-batch`, the storage
 * mock). The PDF downloads through the signed URL. The proxy refuses the print route and the api's
 * internal snapshot read. Axe and reflow at 320 px and 1440 px. The PDF is kept as the sample CI's
 * veraPDF step checks (`scripts/verapdf`). Story 13.9: «Rapport» states the deletion date, locked
 * and open, and it follows the Testfrist. What the api refuses is
 * `backend/tests/reports/test_student_report.py`. */
const copy = nb.reports.download;
const CSRF = { "X-Requested-With": "olspillet" };
export const SAMPLE = path.join("test-results", "student-report.pdf");

test("a Student makes and downloads the Student report once the Testfrist has passed", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // Invitations through the worker, a Class session, a lock and a real PDF render
  const { gameId, sessionId, students } = await liveClassGame(browser, lecturerSession, 1, {
    aiMode: "rule_based",
    obligatory: true,
    width: VIEWPORTS[2]!.width,
    gameSettings: { weeks: 20 },
  });
  const [sara] = students as [(typeof students)[number]];
  try {
    // Story 13.8: the game played to its end, so the sample report holds the game with its charts.
    await orderByApi(sara, gameId, 1, 4);
    const played = await sara.context.request.post(`/api/dev/games/${gameId}/playout`, { headers: CSRF });
    expect(played.status()).toBe(200);
    const steps = await sara.context.request.post(`/api/dev/class-sessions/${sessionId}/replay-done`, {
      headers: CSRF,
    });
    expect(steps.status()).toBe(204);
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
    await page.reload();
    await expect(report).toHaveAttribute("data-state", "current");
    const make = report.getByRole("button", { name: copy.make });
    await expect(make).toBeVisible();
    await expect(report).toContainText(copy.note);
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
