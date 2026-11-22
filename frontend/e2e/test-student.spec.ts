import { type Browser, type BrowserContext, expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, loginByApi, nextMail } from "./support/auth";
import { expectAccessible, test } from "./support/classes";

/** Test students who consent before they take part (Story 12.8, FR-82, AD-27, UX-DR57), on the
 * local stack with `worker-batch`: the Admin's Control test invites a fresh address, which
 * registers as a test student; the Klasseliste labels them «Teststudent» with their consent in
 * text; on Hjem they read what the Control test is for and who the data controller is, decline,
 * and consent after all; until then the Klasseøkt's «Fordeling» says how many have not
 * consented. Each viewport makes its own Control test in an Institution it marks first. The rules
 * (the mark, the Roster rule both ways, the consent rows, every seating path) are pinned by
 * `backend/tests/sessions/test_test_students.py`. */
const consent = nb.homes.consent;
const registration = nb.classes.registration;
const CSRF = { "X-Requested-With": "olspillet" };

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const tag = () => `${Date.now()}${Math.floor(Math.random() * 1e6)}`;

type ControlTest = { id: string; class_id: string; name: string };

/** A Control test of the Admin in an Institution marked as the operator's just now, through the
 * api (the screens are Story 12.7's). */
async function controlTest(admin: Page): Promise<ControlTest> {
  const institution = await admin.request.post("/api/admin/institutions", {
    data: { name: `Operatøren ${tag()}` },
    headers: CSRF,
  });
  expect(institution.status()).toBe(201);
  const marked = await admin.request.put(`/api/admin/institutions/${(await institution.json()).id}/operator-owned`, {
    headers: CSRF,
  });
  expect(marked.status()).toBe(200);
  const page = await (await admin.request.get("/api/admin/control-tests")).json();
  const name = `Kontrolltest ${tag()}`;
  const created = await admin.request.post("/api/admin/control-tests", {
    data: { name, scoring_guide_id: page.scoring_guides[0].id, model_config_id: page.model_configs[0].id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  return { ...((await created.json()) as ControlTest), name };
}

/** Invite `address` to the Control test's Roster and register them through the mailed link, in
 * a context of their own: a test student, logged in. */
async function testStudent(admin: Page, browser: Browser, test_: ControlTest, address: string, vp: (typeof VIEWPORTS)[number]) {
  const before = await latestMail(admin, address);
  const staged = await admin.request.post(`/api/classes/${test_.class_id}/roster-paste`, {
    data: { text: address },
    headers: CSRF,
  });
  expect(staged.status()).toBe(201);
  const sent = await admin.request.post(`/api/classes/${test_.class_id}/invitations`, {
    data: { upload_id: (await staged.json()).id, valid_days: 14 },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  const token = (await nextMail(admin, address, before)).text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  const context: BrowserContext = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: vp.width, height: vp.height },
  });
  const accepted = await context.request.post("/api/auth/invitation/accept", {
    data: { token, name: "Tea Teststudent", password: "et-godt-passord" },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  expect((await accepted.json()).user.is_test_student).toBe(true);
  return context.newPage();
}

async function rosterLine(admin: Page, test_: ControlTest, address: string) {
  await admin.goto(`/klasser/${test_.class_id}`);
  await expect(admin.getByText(nb.classes.page.controlTestRoster)).toBeVisible();
  return admin.getByRole("listitem").filter({ hasText: address });
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a test student is listed, declines on Hjem, consents after all, and the allocation waits for it", async ({
      page,
      browser,
    }) => {
      test.slow();
      await loginByApi(page, "admin");
      const made = await controlTest(page);
      const address = `teststudent-${vp.width}-${tag()}@stud.example.no`;
      const student = await testStudent(page, browser, made, address, vp);

      // The Klasseliste: «Teststudent», not answered yet.
      const row = await rosterLine(page, made, address);
      await expect(row).toContainText(`${registration.testStudent} · ${registration.consent.pending}`);
      await expectAccessible(page, vp.phone);

      // «Fordeling» says how many have not consented.
      await page.goto(`/klasseokter/${made.id}`);
      await expect(page.getByText(nb.sessions.allocation.consentMissing(1))).toBeVisible();

      // Hjem: the purpose and the data controller, then «Nei takk».
      await student.goto("/hjem");
      const block = student.getByRole("region", { name: consent.title });
      await expect(block.getByText(consent.purpose)).toBeVisible();
      await expect(block.getByText(consent.controller)).toBeVisible();
      await expectAccessible(student, vp.phone);
      await block.getByRole("button", { name: consent.decline }).click();
      await expect(block.getByRole("status")).toHaveText(consent.declined);
      await expect(block.getByRole("status")).toBeFocused();
      await expectAccessible(student, vp.phone);
      await expect(await rosterLine(page, made, address)).toContainText(registration.consent.declined);

      // «Jeg samtykker likevel»: one line with the day, and the block is gone.
      await block.getByRole("button", { name: consent.giveAfterAll }).click();
      const given = student.getByRole("status").filter({ hasText: "Du samtykket" });
      await expect(given).toBeVisible();
      await expect(given).toBeFocused();
      await expect(student.getByRole("region", { name: consent.title })).toHaveCount(0);
      await expectAccessible(student, vp.phone);
      await expect(await rosterLine(page, made, address)).toContainText(
        `${registration.testStudent} · ${registration.consent.given}`,
      );
      await page.goto(`/klasseokter/${made.id}`);
      await expect(page.getByRole("heading", { name: nb.sessions.allocation.title })).toBeVisible();
      await expect(page.getByText(nb.sessions.allocation.consentMissing(1))).toHaveCount(0);
    });
  });
}
