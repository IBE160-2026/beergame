import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, lecturerPage, test, VIEWPORTS } from "./support/classes";

/** «Pseudonymisert eksport» in the Admin-område (Story 15.4, FR-71, FR-77, NFR-6), on the local
 * stack. Each test makes a fresh Class session through the api. The stack keeps one key
 * fingerprint for all runs, so every test first sets it to `KEY` (the same key again changes
 * nothing). What the ZIP holds, the scope and the key search are pinned by
 * `backend/tests/ops/test_evaluation_export.py`. */
const copy = nb.admin.evaluation;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const KEY = "e2e-nokkel-for-pseudonymer-0123456789-abcdefghij";
const OTHER_KEY = "en-annen-nokkel-for-pseudonymer-9876543210-zyx";

/** A saved Class session with its four dates, and how the page names it. */
async function savedSession(lecturer: Page): Promise<{ id: string; label: string }> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  const session = await created.json();
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await lecturer.request.put(`/api/class-sessions/${session.id}`, {
    data: { ai_mode: session.ai_mode, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  return { id: session.id, label: copy.sessions.label(klass.name, 1) };
}

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin records an agreement and downloads the export with the key holder's key", async ({
      page,
      browser,
      lecturerSession,
    }) => {
      const lecturer = await lecturerPage(browser, lecturerSession, vp);
      const { label } = await savedSession(lecturer);

      // A Lecturer gets the permission-denied page and no form.
      await lecturer.goto("/admin/evaluering");
      await expect(lecturer.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
      await expect(lecturer.getByLabel(copy.run.key)).toHaveCount(0);

      await loginByApi(page, "admin");
      const keySet = await page.request.post("/api/admin/evaluation/key", { data: { key: KEY }, headers: CSRF });
      expect(keySet.status()).toBe(200);
      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.evaluation }).click();
      await expect(page).toHaveURL(/\/admin\/evaluering$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();

      // No agreement yet: the Class session is not among those to export.
      const sessions = page.getByRole("region", { name: copy.sessions.title });
      const row = sessions.locator("tbody tr").filter({ hasText: label });
      await expect(row).toContainText(copy.sessions.noAgreement);
      const run = page.getByRole("region", { name: copy.run.title });
      await expect(run.getByRole("checkbox", { name: label })).toHaveCount(0);

      await row.getByRole("button", { name: copy.sessions.record(label) }).click();
      await row.getByLabel(copy.agreementForm.agreedBy).fill("Prorektor for utdanning");
      await row.getByLabel(copy.agreementForm.agreedOn).fill("2026-11-01");
      await row.getByLabel(copy.agreementForm.controller).fill("Demohøgskolen");
      await row.getByRole("button", { name: copy.agreementForm.save }).click();
      await expect(row.getByRole("status")).toHaveText(copy.agreementForm.saved(label));
      await expect(row).toContainText(copy.sessions.controller("Demohøgskolen"));
      await expectAccessible(page, vp.phone);

      // The run: the Class session, the key, one press; the ZIP downloads and the key field empties.
      const choice = run.getByRole("checkbox", { name: label });
      await choice.check();
      const keyField = run.getByLabel(copy.run.key, { exact: true });
      await keyField.fill(KEY);
      const download = page.waitForEvent("download");
      await run.getByRole("button", { name: copy.run.submit }).click();
      const file = await download;
      expect(file.suggestedFilename()).toMatch(/^pseudonymisert-eksport-\d{8}-\d{6}\.zip$/);
      await expect(run.getByRole("status")).toHaveText(copy.run.done(file.suggestedFilename()));
      await expect(keyField).toHaveValue("");

      // The export list names the run with the Class session's deletion date.
      const exports = page.getByRole("region", { name: copy.exports.title });
      const listed = exports.locator("tbody tr").filter({ hasText: label }).first();
      await expect(listed).toContainText(copy.exports.outcomes.exported);
      await expect(listed).toContainText("slettes");

      // Another key is refused, with the reason beside the form; the list names the refusal.
      await keyField.fill(OTHER_KEY);
      await run.getByRole("button", { name: copy.run.submit }).click();
      await expect(run.getByRole("alert")).toHaveText(copy.run.keyChanged);
      await expect(keyField).toHaveValue("");
      await expect(exports.locator("tbody tr").filter({ hasText: label }).first()).toContainText(
        copy.exports.outcomes.pseudonym_key_changed,
      );
      await expectAccessible(page, vp.phone);
    });
  });
}
