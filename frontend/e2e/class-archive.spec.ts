import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, nextMail } from "./support/auth";
import { expectAccessible, freshLecturer, VIEWPORTS } from "./support/classes";

/** Archiving a Class (Story 4.10, FR-6, NFR-6, UX-DR56), on the local stack. A fresh Lecturer
 * archives a fresh Class that has sent one Student Invitation: the consequence stands above the
 * button, the page turns read-only, the Lærerhjem lists it under «Arkiverte Klasser», and the
 * mailed link shows the expired-link state. Needs `worker-batch` running. The demo Class is never
 * archived. The rule on every route is pinned by `backend/tests/classes/test_archive.py`. */
const copy = nb.classes.archive;
const CSRF = { "X-Requested-With": "olspillet" };

async function freshClass(lecturer: Page, prefix: string): Promise<{ id: string; name: string }> {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const name = `${prefix}-${Date.now() % 100000}${Math.floor(Math.random() * 100)}`;
  const created = await lecturer.request.post("/api/classes", {
    data: { name, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  return { id: (await created.json()).id as string, name };
}

test("the Faglærer archives a Class: read-only, listed apart, and its open link no longer works", async ({
  page,
  browser,
}) => {
  test.setTimeout(90_000);
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer, "arkiv");
  const student = `arkiv-${Date.now()}${Math.floor(Math.random() * 1e6)}@stud.example.no`;
  const before = await latestMail(page, student);
  const staged = await lecturer.request.post(`/api/classes/${klass.id}/roster-paste`, {
    data: { text: student },
    headers: CSRF,
  });
  const sent = await lecturer.request.post(`/api/classes/${klass.id}/invitations`, {
    data: { upload_id: (await staged.json()).id, valid_days: 14 },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  const mail = await nextMail(page, student, before);
  const link = mail.text.match(/https?:\/\/[^/\s]+(\/invitasjon#[A-Za-z0-9_-]+)/)![1];

  await lecturer.goto(`/klasser/${klass.id}`);
  await expect(lecturer.getByRole("button", { name: nb.classes.entries.add })).toBeVisible();
  const opener = lecturer.getByRole("button", { name: copy.open, exact: true });
  // «Avbryt» closes the panel and returns focus to the opener.
  await opener.click();
  await expect(lecturer.getByRole("button", { name: copy.submit, exact: true })).toBeFocused();
  await lecturer.getByRole("button", { name: copy.cancel }).click();
  await expect(opener).toBeFocused();
  await expect(lecturer.getByText(copy.consequence)).toHaveCount(0);

  // The consequence stands above the button before it is pressed.
  await opener.click();
  const panel = lecturer.getByRole("group", { name: copy.panelTitle });
  const consequence = panel.getByText(copy.consequence);
  const submit = panel.getByRole("button", { name: copy.submit });
  await expect(consequence).toBeVisible();
  const [above, button] = [await consequence.boundingBox(), await submit.boundingBox()];
  expect(above!.y + above!.height).toBeLessThanOrEqual(button!.y);
  await submit.click();

  // Read-only: the notice has focus; no Roster change, no Invitation, no archive again.
  await expect(lecturer.getByText(copy.notice)).toBeFocused();
  await expect(lecturer.getByRole("button", { name: nb.classes.entries.add })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: nb.classes.entries.manual })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.open, exact: true })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: /^Send påminnelse/ })).toHaveCount(0);
  await expect(lecturer.getByRole("heading", { level: 2, name: nb.classes.roster.title })).toBeVisible();
  // The staff page lists the staff with no form and no «Fjern».
  await lecturer.getByRole("link", { name: nb.classes.page.staff }).click();
  await expect(lecturer.getByRole("heading", { level: 1, name: nb.classes.staff.title })).toBeVisible();
  await expect(lecturer.getByText(copy.notice)).toBeVisible();
  await expect(lecturer.getByRole("button", { name: nb.classes.staff.addLecturer, exact: true })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: new RegExp(`^${nb.classes.staff.remove} `) })).toHaveCount(0);

  // The Lærerhjem: under «Arkiverte Klasser», marked in text.
  await lecturer.goto("/laererhjem");
  const archived = lecturer.getByRole("region", { name: copy.homeTitle });
  await expect(archived.getByRole("link", { name: klass.name })).toBeVisible();
  await expect(archived.getByRole("listitem").filter({ hasText: klass.name })).toContainText(copy.marker);
  await expect(lecturer.getByRole("region", { name: nb.classes.home.title }).getByRole("link", { name: klass.name })).toHaveCount(0);

  // The mailed link: the expired-link state, and no one joins.
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const own = await context.newPage();
  await own.goto(link);
  await expect(own.getByText(nb.auth.invitation.invalid)).toBeVisible();
  await expect(own.getByLabel(nb.auth.invitation.password)).toHaveCount(0);
  // No new Invitation can come from an archived Class, so none is offered (Issue #93).
  await expect(own.getByRole("button", { name: nb.auth.invitation.requestNew })).toHaveCount(0);
  await context.close();
});

test("a Student whose only Class is archived is told so on Hjem", async ({ page, browser }) => {
  test.setTimeout(90_000);
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer, "eneste");
  const address = `eneste-${Date.now()}${Math.floor(Math.random() * 1e6)}@stud.example.no`;
  const before = await latestMail(page, address);
  const staged = await lecturer.request.post(`/api/classes/${klass.id}/roster-paste`, {
    data: { text: address },
    headers: CSRF,
  });
  const sent = await lecturer.request.post(`/api/classes/${klass.id}/invitations`, {
    data: { upload_id: (await staged.json()).id, valid_days: 14 },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  const mail = await nextMail(page, address, before);
  const link = mail.text.match(/https?:\/\/[^/\s]+(\/invitasjon#[A-Za-z0-9_-]+)/)![1];
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const student = await context.newPage();
  await student.goto(link);
  await student.getByLabel(nb.auth.invitation.name).fill("Eneste Student");
  await student.getByLabel(nb.auth.invitation.password).fill("et-langt-passord");
  await student.getByRole("button", { name: nb.auth.invitation.submit }).click();
  await expect(student).toHaveURL(/\/hjem$/);
  await expect(student.getByRole("heading", { level: 2, name: klass.name })).toBeVisible();

  const archived = await lecturer.request.post(`/api/classes/${klass.id}/archive`, { headers: CSRF });
  expect(archived.status()).toBe(200);
  await student.reload();
  // Not an empty page: Hjem says there is no Class now (Issue #93).
  await expect(student.getByText(nb.homes.noClass)).toBeVisible();
  await expect(student.getByRole("heading", { level: 2, name: klass.name })).toHaveCount(0);
  await context.close();
});

test("a page left open turns read-only when another Faglærer has archived the Class", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const klass = await freshClass(lecturer, "stale");
  await lecturer.goto(`/klasser/${klass.id}`);
  await lecturer.getByRole("button", { name: nb.classes.entries.add }).click();
  // Archived meanwhile, as by a co-owner in another browser.
  const archived = await lecturer.request.post(`/api/classes/${klass.id}/archive`, { headers: CSRF });
  expect(archived.status()).toBe(200);
  await lecturer.getByLabel(nb.classes.entries.email).fill("ny@stud.example.no");
  await lecturer.getByRole("button", { name: nb.classes.entries.addSubmit, exact: true }).click();
  // The refusal reads the Class again: the forms go, and focus moves to the notice saying why.
  await expect(lecturer.getByText(copy.notice)).toBeFocused();
  // The refusal itself is announced, though the form that was refused has closed (Issue #93).
  await expect(lecturer.getByRole("alert").filter({ hasText: copy.refused })).toBeVisible();
  await expect(lecturer.getByRole("button", { name: nb.classes.entries.add })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.open, exact: true })).toHaveCount(0);
});

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(`An archived Class, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the archive panel, the archived Class page and the Lærerhjem pass axe with no horizontal scroll", async ({
      page,
      browser,
    }) => {
      const lecturer = await freshLecturer(page, browser);
      const active = await freshClass(lecturer, "aktiv");
      const done = await freshClass(lecturer, "arkivert");
      const archived = await lecturer.request.post(`/api/classes/${done.id}/archive`, { headers: CSRF });
      expect(archived.status()).toBe(200);

      await lecturer.goto(`/klasser/${active.id}`);
      await lecturer.getByRole("button", { name: copy.open, exact: true }).click();
      await expect(lecturer.getByText(copy.consequence)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      await lecturer.goto(`/klasser/${done.id}`);
      await expect(lecturer.getByText(copy.notice)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      await lecturer.goto("/laererhjem");
      await expect(lecturer.getByRole("region", { name: copy.homeTitle }).getByRole("link", { name: done.name })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
