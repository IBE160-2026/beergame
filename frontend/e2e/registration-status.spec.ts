import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, nextMail } from "./support/auth";
import { expectAccessible, freshLecturer, VIEWPORTS } from "./support/classes";

/** Registration status and reminders (Story 4.7, FR-9, NFR-6, NFR-10), on the local stack at
 * 320 px, 200 % text and 1440 px. A fresh Lecturer sends three Invitations, one of which bounces
 * hard through the dev stand-in for the provider. «Status etter utsending» shows the totals as
 * text and every address with its status; the list filters and searches; a reminder to all
 * leaves out and names the hard bounce, and a single address gets its own. Needs `worker-batch`
 * running. */
const copy = nb.classes.registration;
const CSRF = { "X-Requested-With": "olspillet" };

async function sentClass(lecturer: Page, addresses: string[]): Promise<string> {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const created = await lecturer.request.post("/api/classes", {
    data: { name: `status-${Date.now() % 100000}`, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  const classId = (await created.json()).id as string;
  const staged = await lecturer.request.post(`/api/classes/${classId}/roster-paste`, {
    data: { text: addresses.join("\n") },
    headers: CSRF,
  });
  expect(staged.status()).toBe(201);
  const sent = await lecturer.request.post(`/api/classes/${classId}/invitations`, {
    data: { upload_id: (await staged.json()).id, valid_days: 14 },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  for (const address of addresses) await nextMail(lecturer, address, null);
  return classId;
}

for (const vp of VIEWPORTS) {
  test.describe(`registration status, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Lecturer follows each address and sends reminders", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser, vp.text200);
      const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
      const [ola, kari, per] = ["ola", "kari", "per"].map((n) => `${n}-${tag}@stud.example.no`);
      const classId = await sentClass(lecturer, [ola, kari, per]);
      const bounced = await lecturer.request.post("/api/dev/mailbox/bounce", {
        data: { to: per, bounce_class: "hard" },
        headers: CSRF,
      });
      expect(bounced.status()).toBe(200);

      await lecturer.goto(`/klasser/${classId}`);
      const section = lecturer.getByRole("region", { name: copy.title });
      await expect(section).toBeVisible();
      for (const text of [
        copy.total(copy.registered, 0),
        copy.total(copy.manual, 0),
        copy.total(copy.unregistered, 3),
      ]) {
        await expect(section.getByText(text, { exact: true })).toBeVisible();
      }
      const list = section.getByRole("region", { name: copy.listTitle });
      const rows = list.getByRole("listitem");
      await expect(rows).toHaveCount(3);
      await expect(rows.filter({ hasText: ola })).toContainText("Invitert, gyldig til og med");
      await expect(rows.filter({ hasText: per })).toContainText(nb.classes.invitations.bounceStatus("hard"));
      await expect(rows.filter({ hasText: per }).getByRole("button")).toHaveCount(0);

      // Filter by status and search by address.
      await list.getByLabel(copy.filter).selectOption("bounced");
      await expect(rows).toHaveCount(1);
      await list.getByLabel(copy.filter).selectOption("");
      await list.getByLabel(copy.search).fill(`KARI-${tag}`);
      await expect(rows).toHaveCount(1);
      await expect(rows.first()).toContainText(kari);
      await list.getByLabel(copy.search).fill("");
      await expectAccessible(lecturer, vp.phone);

      // A reminder to all: two sent, the hard bounce named.
      const beforeOla = await latestMail(lecturer, ola);
      const link = section.getByRole("button", { name: copy.remindAll(3) });
      await link.click();
      const days = section.getByLabel(nb.classes.roster.validDays);
      await expect(days).toBeFocused();
      await expect(days).toHaveValue("14");
      await expect(section.getByText(copy.confirmLeft(1))).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      await section.getByRole("button", { name: copy.cancel }).click();
      await expect(link).toBeFocused();
      await link.click();
      await days.fill("abc");
      await section.getByRole("button", { name: copy.confirm(2) }).click();
      await expect(section.getByText(nb.classes.roster.validDaysError(1, 60))).toBeVisible();
      await days.fill("7");
      await expect(section.getByText(nb.classes.roster.validDaysError(1, 60))).toHaveCount(0);
      await section.getByRole("button", { name: copy.confirm(2) }).click();
      const result = section.getByRole("status").filter({ hasText: "påminnelser sendt" });
      await expect(result).toContainText("2 påminnelser sendt. Gyldige til og med");
      await expect(result).toContainText(copy.leftOut);
      await expect(result).toContainText(per);
      const mail = await nextMail(lecturer, ola, beforeOla);
      expect(mail.text).toMatch(/\/invitasjon#/);

      // One address alone.
      const beforeKari = await latestMail(lecturer, kari);
      await rows.filter({ hasText: kari }).getByRole("button", { name: copy.resendFor(kari) }).click();
      await expect(result).toHaveCount(0); // a new action clears the last result line
      await rows.filter({ hasText: kari }).getByRole("button", { name: copy.resend, exact: true }).click();
      await expect(section.getByRole("status").filter({ hasText: kari })).toContainText("Ny Invitasjon sendt");
      await nextMail(lecturer, kari, beforeKari);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}
