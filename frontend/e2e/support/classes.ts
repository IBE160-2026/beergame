import { test as base, type Browser, type BrowserContext, expect, type Page } from "@playwright/test";

import { demoSession, latestMail, nextMail, untilFontsLoaded } from "./auth";
import { axe } from "./axe";

/** Shared by the Class specs (Stories 4.1, 4.2): the viewports of NFR-6, the axe and layout
 * check, and a fresh Lecturer made from an Invitation, so the demo Lecturer's Classes stay as the
 * seed left them. */
const CSRF = { "X-Requested-With": "olspillet" };

export type Viewport = { name: string; width: number; height: number; phone: boolean; text200?: boolean };

export const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "200 % text", width: 1280, height: 800, phone: false, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

export async function expectAccessible(page: Page, phone: boolean) {
  // The reflow and tap-target checks below measure the layout: measure it in the product's font.
  await untilFontsLoaded(page);
  const results = await axe(page);
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  await expectReflow(page, phone);
}

/** The layout half of `expectAccessible`: no page scroll, and on phone every control of `main` a
 * 44 px tap target. For the further states of a screen whose one axe check is made in another. */
export async function expectReflow(page: Page, phone: boolean) {
  await untilFontsLoaded(page);
  const scrolls = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(scrolls).toBe(false);
  if (!phone) return;
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("main a, main button, main input, main select")]
      .filter((el) => el.offsetParent !== null)
      .map((el) => ({ name: el.id || el.textContent?.trim(), ...el.getBoundingClientRect().toJSON() }))
      .filter((b) => b.height < 44 || b.width < 44),
  );
  expect(small).toEqual([]);
}

/** A fresh Lecturer, made from an Invitation, logged in on a page of its own. */
export async function freshLecturer(page: Page, browser: Browser, text200 = false): Promise<Page> {
  return (await freshLecturerWithAddress(page, browser, text200)).page;
}

/** As `freshLecturer`, with the Lecturer's address (Story 4.9 adds them as co-owner). */
export async function freshLecturerWithAddress(
  page: Page,
  browser: Browser,
  text200 = false,
): Promise<{ page: Page; address: string }> {
  const { session, address } = await invitedLecturer(browser, test.info().project.use.baseURL);
  const viewport = page.viewportSize();
  const own = await lecturerPage(browser, session, { width: viewport!.width, height: viewport!.height, text200 });
  return { page: own, address };
}

export type Session = Awaited<ReturnType<BrowserContext["storageState"]>>;

/** A new Lecturer: the demo Admin invites the address, and the mailed link is accepted through
 * the api. One mail through the worker. */
async function invitedLecturer(browser: Browser, baseURL?: string): Promise<{ session: Session; address: string }> {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const address = `klasse-${tag}@example.com`;
  const admin = await browser.newContext({ baseURL, storageState: { cookies: [demoSession("admin")], origins: [] } });
  const before = await latestMail(admin, address);
  const sent = await admin.request.post("/api/admin/invitations", {
    data: { email: address, role: "lecturer" },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  const mail = await nextMail(admin, address, before);
  await admin.close();
  const token = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  const context = await browser.newContext({ baseURL });
  const accepted = await context.request.post("/api/auth/invitation/accept", {
    data: { token, name: `Lene${tag} Testesen`, password: "et-godt-passord" },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  const session = await context.storageState();
  await context.close();
  return { session, address };
}

/** A page of its own, logged in with `session`, at the viewport's size (and 200 % text). */
export async function lecturerPage(
  browser: Browser,
  session: Session,
  viewport: Pick<Viewport, "width" | "height" | "text200">,
): Promise<Page> {
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: viewport.width, height: viewport.height },
    storageState: session,
  });
  const own = await context.newPage();
  if (viewport.text200) {
    await own.addInitScript(() => {
      document.addEventListener("DOMContentLoaded", () => {
        const style = document.createElement("style");
        style.textContent = "html { font-size: 200% !important; }";
        document.head.appendChild(style);
      });
    });
  }
  return own;
}

/** Playwright's `test` with `lecturerSession`: one fresh Lecturer per worker, made once and shared
 * by every test of that worker that asks for it. For specs whose tests each make a Class of their
 * own, where a Lecturer per test would only queue one more mail for the worker. */
export const test = base.extend<{ ownContextsClosed: void }, { lecturerSession: Session }>({
  /** Every browser context a test opens of its own (a fresh Lecturer, a second Student, a laptop)
   * closes when the test ends, passed or failed. Left open, its page and its live connection
   * stayed for the rest of the worker's tests: a hundred pages reading again on every change, and
   * a slower browser and stack for every test after. */
  ownContextsClosed: [
    async ({ browser }, use) => {
      const before = new Set(browser.contexts());
      await use();
      const opened = browser.contexts().filter((context) => !before.has(context));
      // A route handler may still be fetching for a live re-read when the test ends; drop the
      // routes first so its disposed response does not fail the test.
      await Promise.all(
        opened.map(async (context) => {
          await context.unrouteAll({ behavior: "ignoreErrors" }).catch(() => undefined);
          for (const page of context.pages()) {
            await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => undefined);
          }
          await context.close().catch(() => undefined);
        }),
      );
    },
    { auto: true },
  ],
  lecturerSession: [
    async ({ browser }, use, workerInfo) => {
      await use((await invitedLecturer(browser, workerInfo.project.use.baseURL)).session);
    },
    { scope: "worker" },
  ],
});

/** A fresh Class of `lecturer`, at the demo Institution, made through the api (Story 5.1). */
export async function freshClass(lecturer: Page): Promise<{ id: string; name: string }> {
  const places = await lecturer.request.get("/api/classes/institutions");
  const place = ((await places.json()).items as { id: string; name: string }[]).find(
    (item) => item.name === "Demohøgskolen",
  )!;
  const name = `okt-${Date.now() % 100000}${Math.floor(Math.random() * 100)}`;
  const created = await lecturer.request.post("/api/classes", {
    data: { name, institution_id: place.id },
    headers: CSRF,
  });
  expect(created.status()).toBe(201);
  return { id: (await created.json()).id as string, name };
}
