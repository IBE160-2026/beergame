import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { nextMail } from "./support/auth";
import { expectAccessible, freshLecturer, type Viewport } from "./support/classes";

/** What became of the Invitations (Story 4.6, FR-8, NFR-6, NFR-10), on the local stack at 320 and
 * 1440 px. A fresh Lecturer sends three Invitations; two of the mails then bounce, one hard and
 * one soft, through the dev stand-in for the provider (`POST /api/dev/mailbox/bounce`, a signed
 * event through the webhook's own handler). The Class page shows the four counts and the bounced
 * addresses with their status in text. Needs `worker-batch` running. */
const copy = nb.classes.invitations;
const CSRF = { "X-Requested-With": "olspillet" };

const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

/** A Class of the Lecturer's with Invitations sent to `addresses`, every mail out; its id. */
async function sentClass(lecturer: Page, addresses: string[]): Promise<string> {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const created = await lecturer.request.post("/api/classes", {
    data: { name: `bounce-${Date.now() % 100000}`, institution_id: place.id },
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

async function bounce(page: Page, address: string, bounceClass: "hard" | "soft") {
  const answer = await page.request.post("/api/dev/mailbox/bounce", {
    data: { to: address, bounce_class: bounceClass },
    headers: CSRF,
  });
  expect(answer.status()).toBe(200);
}

/** The definition under the count labelled `label` in «Invitasjoner». */
function count(page: Page, label: string) {
  const section = page.getByRole("region", { name: copy.title });
  return section
    .locator("dl > div")
    .filter({ has: page.getByRole("term").filter({ hasText: new RegExp(`^${label}$`) }) })
    .getByRole("definition");
}

test("the counts on an open Class page follow a bounce without a reload", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const [ola, kari] = ["ola", "kari"].map((n) => `${n}-${tag}@stud.example.no`);
  const classId = await sentClass(lecturer, [ola, kari]);
  // The page's own clock, so the 15 s refresh is run forward instead of waited for.
  await lecturer.clock.install();
  await lecturer.goto(`/klasser/${classId}`);
  await expect(count(lecturer, copy.sent)).toHaveText("2");
  await expect(count(lecturer, copy.bounced)).toHaveText("0");
  const section = lecturer.getByRole("region", { name: copy.title });
  await expect(section.getByRole("listitem")).toHaveCount(0);

  await bounce(lecturer, ola, "hard");
  await lecturer.clock.fastForward(16_000);
  await expect(count(lecturer, copy.bounced)).toHaveText("1");
  await expect(section.getByRole("listitem").filter({ hasText: ola })).toContainText(copy.bounceStatus("hard"));
  await lecturer.context().close();
});

for (const vp of VIEWPORTS) {
  test.describe(`bounces and counts, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Class page counts the Invitations and names the addresses the mail did not reach", async ({
      page,
      browser,
    }) => {
      const lecturer = await freshLecturer(page, browser);
      const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
      const [ola, kari, per] = ["ola", "kari", "per"].map((n) => `${n}-${tag}@stud.example.no`);
      const classId = await sentClass(lecturer, [ola, kari, per]);
      await bounce(lecturer, ola, "hard");
      await bounce(lecturer, kari, "soft");

      await lecturer.goto(`/klasser/${classId}`);
      const section = lecturer.getByRole("region", { name: copy.title });
      await expect(section).toBeVisible();
      const counts = section.locator("dl > div");
      for (const [label, value] of [
        [copy.sent, "3"],
        [copy.bounced, "2"],
        [copy.accepted, "0"],
        [copy.expired, "0"],
      ]) {
        const item = counts.filter({ has: lecturer.getByRole("term").filter({ hasText: new RegExp(`^${label}$`) }) });
        await expect(item.getByRole("definition")).toHaveText(value);
      }
      await expect(section.getByRole("heading", { level: 3, name: copy.bouncedTitle })).toBeVisible();
      const rows = section.getByRole("listitem");
      await expect(rows).toHaveCount(2);
      await expect(rows.filter({ hasText: ola })).toContainText(copy.bounceStatus("hard"));
      await expect(rows.filter({ hasText: kari })).toContainText(copy.bounceStatus("soft"));
      await expect(section.getByText(per)).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}
