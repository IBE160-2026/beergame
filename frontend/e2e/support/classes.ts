import AxeBuilder from "@axe-core/playwright";
import { type Browser, expect, type Page, test } from "@playwright/test";

import { demoContext, latestMail, nextMail } from "./auth";

/** Shared by the Class specs (Stories 4.1, 4.2): the viewports of NFR-6, the axe and layout
 * check, and a fresh Lecturer made from an Invitation, so the demo Lecturer's Classes stay as the
 * seed left them. */
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const CSRF = { "X-Requested-With": "olspillet" };

export type Viewport = { name: string; width: number; height: number; phone: boolean; text200?: boolean };

export const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "200 % text", width: 1280, height: 800, phone: false, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

export async function expectAccessible(page: Page, phone: boolean) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
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
  const tag = `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
  const address = `klasse-${tag}@example.com`;
  const admin = await demoContext(browser, "admin");
  const before = await latestMail(page, address);
  const sent = await admin.request.post("/api/admin/invitations", {
    data: { email: address, role: "lecturer" },
    headers: CSRF,
  });
  expect(sent.status()).toBe(201);
  await admin.close();
  const mail = await nextMail(page, address, before);
  const token = mail.text.match(/\/invitasjon#([A-Za-z0-9_-]+)/)![1];
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: page.viewportSize(),
  });
  const accepted = await context.request.post("/api/auth/invitation/accept", {
    data: { token, name: `Lene${tag} Testesen`, password: "et-godt-passord" },
    headers: CSRF,
  });
  expect(accepted.status()).toBe(200);
  const own = await context.newPage();
  if (text200) {
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
