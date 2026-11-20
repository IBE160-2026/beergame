import { type Browser, expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { latestMail, nextMail } from "./support/auth";
import { expectAccessible, lecturerPage, test, VIEWPORTS } from "./support/classes";

/** Manual registration and single addresses (Story 4.8, FR-7, FR-9, NFR-6, UX-DR47), on the local
 * stack at 320 px and 1440 px. A fresh Lecturer (one per worker) with a fresh Class per test adds
 * one address, registers a Student by hand from the «Klasseliste» Lenke and from an invalid pasted
 * row, removes the Student and puts the address back. The Student sets a password through «Nytt
 * passord» from the mail and reaches Hjem. What a test does not look at is set up through the api.
 * Needs `worker-batch` running. Demo accounts are never touched. */
const copy = nb.classes.entries;
const status = nb.classes.registration;
const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "mitt-forste-passord";

async function freshClass(lecturer: Page): Promise<string> {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const created = await lecturer.request.post("/api/classes", {
    data: { name: `manuelt-${Date.now() % 100000}`, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

/** Whether `email` (with its password) reaches the Class as a Student: 200 or 403. */
async function reaches(browser: Browser, email: string, classId: string): Promise<number> {
  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const login = await context.request.post("/api/auth/login", {
    data: { email, password: PASSWORD },
    headers: CSRF,
  });
  expect(login.status()).toBe(200);
  const found = (await context.request.get(`/api/classes/enrolled/${classId}`)).status();
  await context.close();
  return found;
}

/** «Legg til adresse» through the api: the address on the Roster, not invited. */
async function addEntry(lecturer: Page, classId: string, email: string) {
  const added = await lecturer.request.post(`/api/classes/${classId}/roster/entries`, {
    data: { email },
    headers: CSRF,
  });
  expect(added.status()).toBe(201);
}

function addresses(...names: string[]): string[] {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  return names.map((n) => `${n}-${tag}@stud.example.no`);
}

for (const vp of VIEWPORTS.filter((v) => !v.text200)) {
  test.describe(`manual registration and single addresses, ${vp.name}`, () => {
    let lecturer: Page;
    let classId: string;

    test.beforeEach(async ({ browser, lecturerSession }) => {
      lecturer = await lecturerPage(browser, lecturerSession, vp);
      classId = await freshClass(lecturer);
    });

    test.afterEach(async () => {
      await lecturer.context().close();
    });

    test("one address is added after its errors, never twice", async () => {
      const [late] = addresses("sen");
      await lecturer.goto(`/klasser/${classId}`);
      const roster = lecturer.getByRole("region", { name: nb.classes.roster.title });

      // One address: refused beside the field until it is right, then «Ikke invitert ennå».
      const addLink = roster.getByRole("button", { name: copy.add, exact: true });
      await addLink.click();
      const field = roster.getByLabel(copy.email);
      await expect(field).toBeFocused();
      await field.fill(late.replace(/\.example\.no$/, ""));
      await roster.getByRole("button", { name: copy.addSubmit, exact: true }).click();
      await expect(field).toHaveAttribute("aria-invalid", "true");
      await expect(roster.getByText(nb.classes.roster.reasons.missing_domain)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      await field.fill(late);
      await expect(roster.getByText(nb.classes.roster.reasons.missing_domain)).toHaveCount(0);
      await roster.getByRole("button", { name: copy.addSubmit, exact: true }).click();
      await expect(roster.getByRole("status").filter({ hasText: copy.added(late) })).toBeFocused();
      const section = lecturer.getByRole("region", { name: status.title });
      const rows = section.getByRole("region", { name: status.listTitle }).getByRole("listitem");
      await expect(rows.filter({ hasText: late })).toContainText(status.status.not_invited);
      // Its first Invitation, never a «ny» one (Issue #91).
      await expect(rows.filter({ hasText: late }).getByRole("button", { name: status.inviteFor(late) })).toHaveText(status.invite);
      await expect(section.getByRole("button", { name: status.remindAll(1) })).toBeVisible();

      // A duplicate is refused beside the field; «Avbryt» returns focus to the Lenke.
      await addLink.click();
      await expect(roster.getByRole("status")).toHaveCount(0); // a new action clears the result line
      await roster.getByLabel(copy.email).fill(late.toUpperCase());
      await roster.getByRole("button", { name: copy.addSubmit, exact: true }).click();
      await expect(roster.getByText(nb.classes.roster.onRoster)).toBeVisible();
      await roster.getByRole("button", { name: copy.cancel }).click();
      await expect(addLink).toBeFocused();
    });

    test("a Student registered by hand sets a password, is removed and put back", async ({ browser }) => {
      const [kari] = addresses("kari");
      await lecturer.goto(`/klasser/${classId}`);
      const roster = lecturer.getByRole("region", { name: nb.classes.roster.title });
      const addLink = roster.getByRole("button", { name: copy.add, exact: true });
      const section = lecturer.getByRole("region", { name: status.title });
      const rows = section.getByRole("region", { name: status.listTitle }).getByRole("listitem");

      // «Registrer manuelt» from the Klasseliste Lenke.
      const before = await latestMail(lecturer, kari);
      await roster.getByRole("button", { name: copy.manual, exact: true }).click();
      await expect(roster.getByLabel(copy.email)).toBeFocused();
      await roster.getByLabel(copy.email).fill(kari);
      await roster.getByRole("button", { name: copy.manualSubmit }).click();
      await expect(roster.getByText(copy.nameEmpty)).toBeVisible();
      await expect(roster.getByLabel(copy.name)).toBeFocused();
      await expectAccessible(lecturer, vp.phone);
      await roster.getByLabel(copy.name).fill("Kari Nordmann");
      await expect(roster.getByText(copy.nameEmpty)).toHaveCount(0);
      await roster.getByRole("button", { name: copy.manualSubmit }).click();
      await expect(roster.getByRole("status").filter({ hasText: copy.registered(kari) })).toBeFocused();
      await expect(rows.filter({ hasText: kari })).toContainText(status.status.registered_manually);
      await expect(section.getByText(status.total(status.manual, 1), { exact: true })).toBeVisible();

      // The Student sets a password through «Nytt passord» and reaches the Class.
      const mail = await nextMail(lecturer, kari, before);
      expect(mail.subject).toBe("Du er registrert i ØL-spillet");
      const link = mail.text.match(/http:\/\/127\.0\.0\.1:8080(\/nytt-passord#[A-Za-z0-9_-]+)/)![1];
      const student = await browser.newContext({ baseURL: test.info().project.use.baseURL });
      const studentPage = await student.newPage();
      await studentPage.goto(link);
      // The account has no password yet: the page asks for a first one (Issue #91).
      await expect(studentPage.getByText(nb.auth.reset.firstLead(kari))).toBeVisible();
      await studentPage.getByLabel(nb.auth.reset.firstPassword, { exact: true }).fill(PASSWORD);
      await studentPage.getByRole("button", { name: nb.auth.reset.submit }).click();
      await expect(studentPage.getByText(nb.auth.reset.done)).toBeFocused();
      await student.close();
      expect(await reaches(browser, kari, classId)).toBe(200);

      // «Fjern»: the consequence before the button; the Student loses access.
      await rows.filter({ hasText: kari }).getByRole("button", { name: copy.removeFor(kari) }).click();
      await expect(section.getByText(copy.removeRegistered(kari))).toBeVisible();
      const remove = section.getByRole("button", { name: copy.removeSubmit });
      await expect(remove).toBeFocused();
      await expectAccessible(lecturer, vp.phone);
      // The Class read again after the removal says it has no Roster now.
      const classRead = lecturer.waitForResponse(
        (r) => new URL(r.url()).pathname === `/api/classes/${classId}` && r.request().method() === "GET",
      );
      await remove.click();
      // Kari was the last address: the list goes, the confirmation stays and takes focus (Issue #97),
      // also once the Class itself has been read again with no Roster.
      const removed = section.getByRole("status").filter({ hasText: copy.removed(kari) });
      await expect(removed).toBeFocused();
      await expect(rows).toHaveCount(0);
      expect((await (await classRead).json()).roster_count).toBe(0);
      await expect(removed).toBeFocused();
      expect(await reaches(browser, kari, classId)).toBe(403);

      // Added again: on the Roster as before, with access and no new registration.
      await addLink.click();
      await roster.getByLabel(copy.email).fill(kari);
      await roster.getByRole("button", { name: copy.addSubmit, exact: true }).click();
      await expect(roster.getByRole("status").filter({ hasText: copy.restored(kari) })).toBeVisible();
      await expect(rows.filter({ hasText: kari })).toContainText(status.status.registered_manually);
      expect(await reaches(browser, kari, classId)).toBe(200);
    });

    test("a row's «Registrer manuelt» opens prefilled, and the page keeps one form open", async () => {
      const [late] = addresses("sen");
      await addEntry(lecturer, classId, late);
      await lecturer.goto(`/klasser/${classId}`);
      const roster = lecturer.getByRole("region", { name: nb.classes.roster.title });
      const addLink = roster.getByRole("button", { name: copy.add, exact: true });
      const section = lecturer.getByRole("region", { name: status.title });
      const rows = section.getByRole("region", { name: status.listTitle }).getByRole("listitem");

      // A row's «Registrer manuelt» opens prefilled; «Avbryt» returns focus to it.
      const rowManual = rows.filter({ hasText: late }).getByRole("button", { name: copy.manualFor(late) });
      await rowManual.click();
      await expect(section.getByLabel(copy.email)).toHaveValue(late);
      await expect(section.getByLabel(copy.email)).toBeFocused();
      await expectAccessible(lecturer, vp.phone);

      // One form on the page: a Klasseliste form closes the row's, and the row's closes it again.
      await addLink.click();
      await expect(roster.getByLabel(copy.email)).toBeFocused();
      await expect(section.getByLabel(copy.email)).toHaveCount(0);
      await expect(rowManual).toHaveAttribute("aria-expanded", "false");
      await rowManual.click();
      await expect(section.getByLabel(copy.email)).toBeFocused();
      await expect(roster.getByLabel(copy.email)).toHaveCount(0);
      await expect(addLink).toHaveAttribute("aria-expanded", "false");
      await section.getByRole("button", { name: copy.cancel }).click();
      await expect(rowManual).toBeFocused();
    });

    test("an invalid pasted row is corrected through «Registrer manuelt»", async () => {
      const [fixed] = addresses("rettet");
      const invalidAddress = fixed.replace(/\.example\.no$/, "");
      await lecturer.goto(`/klasser/${classId}`);
      const roster = lecturer.getByRole("region", { name: nb.classes.roster.title });
      const section = lecturer.getByRole("region", { name: status.title });
      const rows = section.getByRole("region", { name: status.listTitle }).getByRole("listitem");

      await roster.getByRole("button", { name: nb.classes.roster.pasteInstead }).click();
      await roster.getByLabel(nb.classes.roster.pasteLabel).fill(invalidAddress);
      await roster.getByRole("button", { name: nb.classes.roster.pasteContinue }).click();
      const invalid = roster.getByRole("region", { name: /Ugyldige rader/ });
      const rowLink = invalid.getByRole("button", { name: new RegExp(nb.classes.roster.registerManually) });
      await rowLink.click();
      await expect(invalid.getByLabel(copy.email)).toHaveValue(invalidAddress);
      await expect(invalid.getByLabel(copy.email)).toBeFocused();
      await invalid.getByRole("button", { name: copy.cancel }).click();
      await expect(rowLink).toBeFocused();
      await rowLink.click();
      await expectAccessible(lecturer, vp.phone);
      await invalid.getByLabel(copy.email).fill(fixed);
      await invalid.getByLabel(copy.name).fill("Rettet Adresse");
      await invalid.getByRole("button", { name: copy.manualSubmit }).click();
      await expect(roster.getByRole("status").filter({ hasText: copy.registered(fixed) })).toBeFocused();
      await expect(roster.getByText(/Ugyldige rader/)).toHaveCount(0);
      await expect(rows.filter({ hasText: fixed })).toContainText(status.status.registered_manually);
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
