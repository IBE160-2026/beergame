import fs from "node:fs";

import { expect } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { assistantOf, expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";
import { lockedClassGames } from "./support/live-game";

/** The Klasseøkt's «Eksport» block (Story 13.13, FR-59, NFR-6, NFR-7, UX-DR49) on the local stack: a
 * fresh Class session of two Students. The Lecturer presses «Last ned alle Studentrapporter (ZIP)»,
 * reads the pending line, and once the `reports-bulk` job has built the ZIP the download appears
 * without a reload; the file is a ZIP through the signed URL. Axe and reflow at 320 px, 1280 px
 * with 200 % text and 1440 px. The rules are `backend/tests/reports/test_reports_zip.py`. */
const copy = nb.reports.export;
const completion = copy.completion;

test("staff make and download one ZIP of every Student report, and the Completion export, from «Eksport»", async ({ browser, lecturerSession }) => {
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

    // Story 13.14 (FR-60): the Lecturer opens the choice and downloads the Completion export in
    // both formats. The rules of the file are `backend/tests/reports/test_completion_export.py`.
    await expect(block).toContainText(completion.note);
    const opener = block.getByRole("button", { name: completion.action });
    await expect(opener).toHaveAttribute("aria-expanded", "false");
    await expect(block.getByRole("link", { name: completion.csv })).toBeHidden();
    await opener.click();
    await expect(opener).toHaveAttribute("aria-expanded", "true");
    const csvSaved = page.waitForEvent("download");
    await block.getByRole("link", { name: completion.csv }).click();
    const csvFile = await csvSaved;
    expect(csvFile.suggestedFilename()).toMatch(/^fullforingsliste-klasseokt-\d+\.csv$/);
    const text = fs.readFileSync(await csvFile.path(), "utf-8");
    expect(text.startsWith("\ufeffNavn;E-post;Klassespill;")).toBe(true);
    for (const student of locked.students) expect(text).toContain(student.name);
    const xlsxSaved = page.waitForEvent("download");
    await block.getByRole("link", { name: completion.xlsx }).click();
    const xlsxFile = await xlsxSaved;
    expect(xlsxFile.suggestedFilename()).toMatch(/^fullforingsliste-klasseokt-\d+\.xlsx$/);
    expect(fs.readFileSync(await xlsxFile.path()).subarray(0, 2).toString()).toBe("PK");

    // An Assistant lecturer of the Class sees the same ZIP, but not the Completion export, and the
    // export route refuses them.
    const classId = (await (await page.request.get(`/api/class-sessions/${locked.sessionId}`)).json())
      .class_id as string;
    const assistant = await assistantOf(browser, lecturerSession, classId);
    const helper = await assistant.newPage();
    await helper.setViewportSize({ width: 1280, height: 800 });
    await helper.goto(`/klasseokter/${locked.sessionId}`);
    const helperBlock = helper.locator("[data-export]");
    await expect(helperBlock.getByRole("link", { name: copy.zip.action })).toBeVisible();
    await expect(helperBlock).toContainText("med 2 Studentrapporter.");
    await expect(helperBlock.getByRole("button", { name: completion.action })).toHaveCount(0);
    await expect(helperBlock).not.toContainText(completion.note);
    const refused = await helper.request.get(`/api/class-sessions/${locked.sessionId}/completion-export?format=csv`);
    expect(refused.status()).toBe(403);
    await assistant.close();

    // Each width: the block reflows and axe is clean.
    for (const viewport of VIEWPORTS) {
      const view = await lecturerPage(browser, lecturerSession, viewport);
      await view.goto(`/klasseokter/${locked.sessionId}`);
      if (viewport.text200) await view.addStyleTag({ content: "html { font-size: 200% !important; }" });
      await expect(view.locator("[data-export]").getByRole("link", { name: copy.zip.action })).toBeVisible();
      await view.locator("[data-export]").getByRole("button", { name: completion.action }).click();
      await expect(view.locator("[data-export]").getByRole("link", { name: completion.xlsx })).toBeVisible();
      await expectAccessible(view, viewport.phone);
      await view.context().close();
    }
  } finally {
    await page.context().close();
    for (const student of locked.students) await student.context.close();
  }
});
