import { type BrowserContext, expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { answerTo, type DevMail, latestMail, loginByApi, nextMail } from "./support/auth";
import { expectAccessible, freshLecturer } from "./support/classes";

/** Registering as a Student through a mailed Invitation (Story 4.5, FR-4, FR-8, NFR-6), on the
 * local stack with `worker-batch`. One fresh Lecturer and Class send three Invitations; each
 * viewport registers one of them, so the demo Class's Roster is never touched. The rest of the
 * flow (existing accounts, expiry, removal, the Student scope) is pinned by the api tests in
 * `backend/tests/classes/test_student_registration.py`. */
const copy = nb.auth.invitation;
const CSRF = { "X-Requested-With": "olspillet" };
const PASSWORD = "mitt-nye-passord";

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

/** A new Class of the Lecturer with course code «IBE160» that sends Invitations to `addresses`;
 * the link path each mail carries (newer than `before`, the newest mail per address before). */
async function sendTo(lecturer: Page, name: string, addresses: string[], before: (DevMail | null)[]) {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const created = await lecturer.request.post("/api/classes", {
    data: { name, institution_id: place.id, course_code: "IBE160" },
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
  return Promise.all(
    addresses.map(async (address, i) => {
      const mail = await nextMail(lecturer, address, before[i]);
      return mail.text.match(/https?:\/\/[^/\s]+(\/invitasjon#[A-Za-z0-9_-]+)/)![1];
    }),
  );
}

test("a mailed Student Invitation registers the Student by phone and desktop, who lands on Hjem", async ({
  page,
  browser,
}) => {
  test.slow();
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const addresses = VIEWPORTS.map((vp) => `student-${vp.width}-${tag}@stud.example.no`);
  const lecturer = await freshLecturer(page, browser);
  const lecturerName = (await (await lecturer.request.get("/api/auth/me")).json()).user.name as string;
  const name = `reg-${tag}`;
  const links = await sendTo(lecturer, name, addresses, addresses.map(() => null));
  const label = nb.classes.home.label(name, "IBE160");

  for (const [i, vp] of VIEWPORTS.entries()) {
    const context: BrowserContext = await browser.newContext({
      baseURL: test.info().project.use.baseURL,
      viewport: { width: vp.width, height: vp.height },
    });
    const student = await context.newPage();
    await student.goto(links[i]);

    // «Du er invitert»: the Class and its Lecturer, the address locked, the Start-date line.
    await expect(student.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
    await expect(student.getByText(copy.student.lead(lecturerName, label))).toBeVisible();
    const email = student.getByLabel(copy.student.email);
    await expect(email).toHaveValue(addresses[i]);
    await expect(email).toHaveAttribute("readonly", "");
    // The keyboards the fields ask for: text for the name, e-mail and password otherwise.
    await expect(email).toHaveAttribute("type", "email");
    const nameField = student.getByLabel(copy.name);
    await expect(nameField).toHaveAttribute("autocomplete", "name");
    expect(await nameField.evaluate((el: HTMLInputElement) => el.type)).toBe("text");
    const password = student.getByLabel(copy.password);
    await expect(password).toHaveAttribute("type", "password");
    await expect(student.getByText(`${copy.validity(14)} ${copy.student.startDate}`)).toBeVisible();
    await expect(student.locator("main button")).toHaveCount(1);
    await expectAccessible(student, vp.phone);

    // A reason after the first press clears as the field is typed.
    await student.getByRole("button", { name: copy.submit }).click();
    await expect(nameField).toHaveAccessibleDescription(copy.errors.nameEmpty);
    await nameField.fill("Sara Lund");
    await expect(nameField).not.toHaveAttribute("aria-invalid", "true");
    await password.fill(PASSWORD);
    const created = answerTo(student, "/api/auth/invitation/accept");
    await student.getByRole("button", { name: copy.submit }).click();
    expect((await created).status()).toBe(200);

    // Hjem names the Class and repeats when Rolle and spill come.
    await expect(student).toHaveURL(/\/hjem$/);
    await expect(student.getByRole("heading", { level: 2, name: label })).toBeVisible();
    await expect(student.getByText(nb.homes.startDate)).toBeVisible();
    await expectAccessible(student, vp.phone);

    if (!vp.phone) {
      // The used link: the expired-or-used state, with its one action.
      await context.clearCookies();
      await student.goto(links[i]);
      await expect(student.getByText(copy.invalid)).toBeVisible();
      await student.getByRole("button", { name: copy.requestNew }).click();
      await expect(student.getByText(copy.requested)).toBeFocused();

      // A second Class invites the same address: the account logs in and joins, no new User.
      const second = `${name}-b`;
      const before = await latestMail(lecturer, addresses[i]);
      const [link] = await sendTo(lecturer, second, [addresses[i]], [before]);
      // Only the fragment differs from the page open now: leave it, so the new link loads.
      await student.goto("about:blank");
      await student.goto(link);
      await expect(student.getByText(copy.student.existing.lead(nb.classes.home.label(second, "IBE160")))).toBeVisible();
      await expect(student.getByLabel(copy.name)).toHaveCount(0);
      await expectAccessible(student, vp.phone);
      await student.getByLabel(copy.existing.password).fill(PASSWORD);
      const joined = answerTo(student, "/api/auth/invitation/accept-login");
      await student.getByRole("button", { name: copy.student.existing.submit }).click();
      expect((await joined).status()).toBe(200);
      await expect(student).toHaveURL(/\/hjem$/);
      await expect(student.getByRole("heading", { level: 2 })).toHaveText([label, nb.classes.home.label(second, "IBE160")]);
    }
    await context.close();
  }
  await lecturer.context().close();
});

test("Hjem shows the new Class at once when an account joins from a tab that already showed Hjem", async ({
  page,
  browser,
}) => {
  test.slow();
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const address = `student-cache-${tag}@stud.example.no`;
  const lecturer = await freshLecturer(page, browser);
  const first = `cache-${tag}`;
  const [link] = await sendTo(lecturer, first, [address], [null]);

  const context = await browser.newContext({ baseURL: test.info().project.use.baseURL });
  const student = await context.newPage();
  await student.goto(link);
  await student.getByLabel(copy.name).fill("Sara Lund");
  await student.getByLabel(copy.password).fill(PASSWORD);
  const created = answerTo(student, "/api/auth/invitation/accept");
  await student.getByRole("button", { name: copy.submit }).click();
  expect((await created).status()).toBe(200);
  await expect(student).toHaveURL(/\/hjem$/);
  await expect(student.getByRole("heading", { level: 2 })).toHaveText([nb.classes.home.label(first, "IBE160")]);

  // Hjem's Classes are now cached in this tab. A second Class invites the address; the tab moves to
  // the link inside the app, so the cache survives, and joins there.
  const second = `${first}-b`;
  const before = await latestMail(lecturer, address);
  const [link2] = await sendTo(lecturer, second, [address], [before]);
  await student.evaluate(() => Object.assign(window, { __sameDocument: true }));
  await student.evaluate((path) => (window as unknown as { next: { router: { push(p: string): void } } }).next.router.push(path), link2);
  await expect(student.getByText(copy.student.existing.lead(nb.classes.home.label(second, "IBE160")))).toBeVisible();
  await student.getByLabel(copy.existing.password).fill(PASSWORD);
  const joined = answerTo(student, "/api/auth/invitation/accept-login");
  await student.getByRole("button", { name: copy.student.existing.submit }).click();
  expect((await joined).status()).toBe(200);
  await expect(student).toHaveURL(/\/hjem$/);
  await expect(student.getByRole("heading", { level: 2 })).toHaveText([
    nb.classes.home.label(first, "IBE160"),
    nb.classes.home.label(second, "IBE160"),
  ]);
  // No page load in between: the list came from a refetch, not a fresh document.
  expect(await student.evaluate(() => (window as unknown as { __sameDocument?: boolean }).__sameDocument)).toBe(true);
  await context.close();
  await lecturer.context().close();
});

test("the demo Student's Hjem names the seeded demo Class", async ({ page }) => {
  await loginByApi(page, "student");
  await page.goto("/hjem");
  await expect(page.getByRole("heading", { level: 2, name: nb.classes.home.label("class-of-1994", "IBE160") })).toBeVisible();
  await expect(page.getByText(nb.homes.startDate)).toBeVisible();
  // The address of a Class page the Student is not staff of: the permission-denied state.
  await page.goto("/klasser/00000000-0000-4000-8000-000000000000");
  await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
});
