import { type Browser, expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, loginByApi, nextMail } from "./support/auth";
import { expectAccessible, freshLecturer, freshLecturerWithAddress, VIEWPORTS } from "./support/classes";

/** Sharing a Class (Story 4.9, FR-5, FR-10, NFR-6, UX-DR56), on the local stack. A fresh Lecturer
 * with a fresh Class meets the last-owner rule, adds another fresh Lecturer as co-owner, invites
 * an Assistant who accepts from the mail and reads the Class without any action, and removes them
 * again. The demo Assistant reads the demo Class. Needs `worker-batch` running. Demo accounts are
 * never changed. */
const copy = nb.classes.staff;
const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "mitt-forste-passord";

async function freshClass(lecturer: Page): Promise<{ id: string; name: string }> {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const name = `delt-${Date.now() % 100000}`;
  const created = await lecturer.request.post("/api/classes", {
    data: { name, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  return { id: (await created.json()).id as string, name };
}

/** The Assistant accepts the Invitation in a browser of their own and lands on the Lærerhjem. */
async function acceptAsAssistant(page: Page, browser: Browser, address: string, before: unknown): Promise<Page> {
  const mail = await nextMail(page, address, before as Awaited<ReturnType<typeof latestMail>>);
  expect(mail.text).toContain("Du får tilgang bare til denne Klassen.");
  const token = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL, viewport: page.viewportSize() });
  const own = await context.newPage();
  await own.goto(`/invitasjon#${token}`);
  await expect(own.getByText(/invitert deg som Assistent/)).toBeVisible();
  await own.getByLabel(nb.auth.invitation.name).fill("Ada Assistent");
  await own.getByLabel(nb.auth.invitation.password).fill(PASSWORD);
  await own.getByRole("button", { name: nb.auth.invitation.submit }).click();
  await expect(own).toHaveURL(/\/laererhjem$/);
  return own;
}

test("the Faglærer shares the Class with a co-owner and an Assistant, and removes the Assistant", async ({
  page,
  browser,
}) => {
  test.setTimeout(90_000);
  const lecturer = await freshLecturer(page, browser);
  const colleague = await freshLecturerWithAddress(page, browser);
  const klass = await freshClass(lecturer);
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const assistantAddress = `assistent-${tag}@example.com`;

  await lecturer.goto(`/klasser/${klass.id}`);
  await lecturer.getByRole("link", { name: nb.classes.page.staff }).click();
  await expect(lecturer.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
  const lecturers = lecturer.getByRole("region", { name: copy.lecturers });
  const assistants = lecturer.getByRole("region", { name: copy.assistants });
  await expect(lecturers.getByRole("listitem")).toHaveCount(1);
  await expect(lecturers.getByRole("listitem")).toContainText(copy.active);
  await expect(assistants.getByText(copy.assistantScope)).toBeVisible();

  // The last Faglærer cannot leave: the reason stands where the consequence would, with no button
  // that could only be refused, and the Class keeps its owner.
  await lecturers.getByRole("button", { name: new RegExp(`^${copy.remove} `) }).click();
  await expect(lecturers.getByText(copy.lastOwner)).toBeVisible();
  await expect(lecturers.getByRole("button", { name: copy.removeSubmit })).toHaveCount(0);
  await expect(lecturers.getByRole("button", { name: copy.cancel })).toBeFocused();
  await lecturers.getByRole("button", { name: copy.cancel }).click();

  // «Legg til Faglærer»: an address without the role is refused beside the field without account
  // details; the reason clears as the Faglærer types; a Lecturer becomes co-owner.
  const addLink = lecturers.getByRole("button", { name: copy.addLecturer, exact: true });
  await addLink.click();
  const field = lecturers.getByLabel(copy.email);
  await expect(field).toBeFocused();
  await field.fill(assistantAddress);
  await lecturers.getByRole("form").getByRole("button", { name: copy.addLecturerSubmit, exact: true }).click();
  await expect(lecturers.getByText(copy.notLecturer)).toBeVisible();
  await field.fill(colleague.address);
  await expect(lecturers.getByText(copy.notLecturer)).toHaveCount(0);
  await lecturers.getByRole("form").getByRole("button", { name: copy.addLecturerSubmit, exact: true }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: colleague.address })).toBeFocused();
  await expect(lecturers.getByRole("listitem")).toHaveCount(2);
  // The co-owner sees the Class on their Lærerhjem and may manage it.
  await colleague.page.goto("/laererhjem");
  await colleague.page.getByRole("link", { name: klass.name }).click();
  await expect(colleague.page.getByRole("link", { name: nb.classes.page.staff })).toBeVisible();

  // «Inviter Assistent»: the row reads «Invitert …», and the Assistant joins from the mail.
  const before = await latestMail(page, assistantAddress);
  await assistants.getByRole("button", { name: copy.inviteAssistant, exact: true }).click();
  // A new action clears the result line.
  await expect(lecturer.getByRole("status").filter({ hasText: colleague.address })).toHaveCount(0);
  await assistants.getByLabel(copy.email).fill(assistantAddress);
  await assistants.getByRole("button", { name: copy.inviteAssistantSubmit }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: assistantAddress })).toBeFocused();
  await expect(assistants.getByRole("listitem").filter({ hasText: assistantAddress })).toContainText("Invitert, gyldig til og med");
  const assistant = await acceptAsAssistant(page, browser, assistantAddress, before);
  await expect(assistant.getByRole("link", { name: nb.classes.home.newClass })).toHaveCount(0);
  await assistant.getByRole("link", { name: klass.name }).click();
  await expect(assistant.getByRole("heading", { level: 2, name: nb.classes.roster.title })).toBeVisible();
  await expect(assistant.getByText(nb.classes.page.assistantLead)).toBeVisible();
  await expect(assistant.getByRole("link", { name: nb.classes.page.staff })).toHaveCount(0);
  await expect(assistant.getByRole("button", { name: nb.classes.entries.add })).toHaveCount(0);
  await lecturer.reload();
  await expect(assistants.getByRole("listitem").filter({ hasText: assistantAddress })).toContainText(copy.active);

  // Removal: the consequence above the button; the Assistant loses access at the next page.
  await assistants.getByRole("button", { name: new RegExp(`^${copy.remove} .*${assistantAddress}`) }).click();
  await expect(assistants.getByText(/mister tilgangen til Klassen/)).toBeVisible();
  await assistants.getByRole("button", { name: copy.removeSubmit }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: "er fjernet fra Klassen" })).toBeFocused();
  await expect(assistants.getByText(copy.noAssistants)).toBeVisible();
  await assistant.reload();
  await expect(assistant.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
});

test("the demo Assistant reads the demo Class without any action", async ({ page }) => {
  await loginByApi(page, "assistant");
  await page.goto("/laererhjem");
  await expect(page.getByRole("link", { name: nb.classes.home.newClass })).toHaveCount(0);
  await page.getByRole("link", { name: /class-of-1994/ }).click();
  const status = page.getByRole("region", { name: nb.classes.registration.title });
  await expect(status.getByRole("listitem").first()).toBeVisible();
  await expect(status.getByRole("button", { name: nb.classes.entries.remove })).toHaveCount(0);
  await expect(status.getByRole("button", { name: /^Send påminnelse/ })).toHaveCount(0);
  await expectAccessible(page, false);
  await expect(page.getByRole("link", { name: nb.classes.page.staff })).toHaveCount(0);
  // The staff page is the Faglærere's alone.
  await page.goto(page.url() + "/faglaerere");
  await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
});

for (const vp of VIEWPORTS) {
  test.describe(`«Faglærere og assistenter», ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the list and both forms pass axe with no horizontal scroll", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser, vp.text200);
      const klass = await freshClass(lecturer);
      const sent = await lecturer.request.post(`/api/classes/${klass.id}/staff/assistants`, {
        data: { email: `assistent-${Date.now()}@example.com` },
        headers: CSRF,
      });
      expect(sent.status()).toBe(201);
      await lecturer.goto(`/klasser/${klass.id}/faglaerere`);
      await expect(lecturer.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      await lecturer.getByRole("button", { name: copy.addLecturer, exact: true }).click();
      await lecturer.getByRole("form").getByRole("button", { name: copy.addLecturerSubmit, exact: true }).click();
      await expectAccessible(lecturer, vp.phone);
      await lecturer.getByRole("button", { name: copy.inviteAssistant, exact: true }).click();
      // One form at a time: «Legg til Faglærer» closed when «Inviter Assistent» opened.
      await expect(lecturer.getByRole("form").getByRole("button", { name: copy.addLecturerSubmit, exact: true })).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
