import fs from "node:fs";

import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { lockedClassGames } from "./support/live-game";

/** The Klasseøkt's «Eksport» block (Story 13.13, FR-59, NFR-6, NFR-7, UX-DR49) on the local stack: a
 * fresh Class session of two Students. The Lecturer presses «Last ned alle Studentrapporter (ZIP)»,
 * reads the pending line, and once the `reports-bulk` job has built the ZIP the download appears
 * without a reload; the file is a ZIP through the signed URL. Axe and reflow at 320 px, 1280 px
 * with 200 % text and 1440 px. The rules are `backend/tests/reports/test_reports_zip.py`. */
const copy = nb.reports.export;

test("staff make and download one ZIP of every Student report from «Eksport»", async ({ browser, lecturerSession }) => {
  test.slow(); // Invitations through the worker, a Class session, a lock and two renders
  const locked = await lockedClassGames(browser, lecturerSession, 2, { aiMode: "rule_based" });
  const page = await lecturerPage(browser, lecturerSession, VIEWPORTS[2]!);
  try {
    await page.goto(`/klasseokter/${locked.sessionId}`);
    const block = page.locator("[data-export]");
    await expect(block.getByRole("heading", { level: 2 })).toHaveText(copy.title);
    await expect(block).toContainText(copy.zip.note);
    await expect(block.getByRole("status")).toBeAttached();

    await block.getByRole("button", { name: copy.zip.action }).click();
    await expect(block).toContainText(copy.zip.pending);
    const link = block.getByRole("link", { name: copy.zip.action });
    await expect(link).toBeVisible({ timeout: 60_000 });
    await expect(block).toContainText("med 2 Studentrapporter.");
    const saved = page.waitForEvent("download");
    await link.click();
    const download = await saved;
    expect(download.suggestedFilename()).toMatch(/^studentrapporter-klasseokt-\d+\.zip$/);
    const zip = fs.readFileSync(await download.path());
    expect(zip.subarray(0, 2).toString()).toBe("PK");
    for (const student of locked.students) expect(zip.includes(Buffer.from(`${student.name}.pdf`))).toBe(true);

    // Each width: the block reflows and axe is clean.
    for (const viewport of VIEWPORTS) {
      const view = await lecturerPage(browser, lecturerSession, viewport);
      await view.goto(`/klasseokter/${locked.sessionId}`);
      if (viewport.text200) await view.addStyleTag({ content: "html { font-size: 200% !important; }" });
      await expect(view.locator("[data-export]").getByRole("link", { name: copy.zip.action })).toBeVisible();
      await expectAccessible(view, viewport.phone);
      await view.context().close();
    }
  } finally {
    await page.context().close();
    for (const student of locked.students) await student.context.close();
  }
});
