import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { type DemoRole, latestMail, loginByApi, nextMail } from "./support/auth";

/** «Brukere og roller» and its invite form (Story 3.7, FR-1, UX-DR57, UX-DR75, NFR-6), on the
 * local stack. Each test invites its own fresh address, so runs never meet. */
const users = nb.admin.users;
const invite = users.invite;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

type Viewport = {
  name: string;
  width: number;
  height: number;
  role: DemoRole;
  phone: boolean;
  text200?: boolean;
};

/** Widths from the story. 400 % zoom on a 1280 × 1024 screen is a 320 × 256 CSS-pixel viewport;
 * 200 % text doubles the root font size at laptop width (WCAG 1.4.4). */
const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, role: "admin", phone: true },
  { name: "400 % zoom", width: 320, height: 256, role: "admin", phone: true },
  {
    name: "200 % text",
    width: 1280,
    height: 800,
    role: "admin",
    phone: false,
    text200: true,
  },
  {
    name: "1440 px",
    width: 1440,
    height: 900,
    role: "adminLecturer",
    phone: false,
  },
];

async function expectAccessible(page: Page, phone: boolean) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(scrolls).toBe(false);
  if (!phone) return;
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("main a, main button, main input")]
      .filter((el) => el.offsetParent !== null)
      .map((el) => ({
        name: el.id || el.textContent?.trim(),
        ...el.getBoundingClientRect().toJSON(),
      }))
      .filter((b) => b.height < 44 || b.width < 44),
  );
  expect(small).toEqual([]);
}

/** One primary button (the User list below has only secondary ones), and the form in one column: the field, the role choice and the button
 * share their left edge and stack downwards. */
async function expectOneColumnWithOnePrimary(page: Page) {
  await expect(page.locator("main form button")).toHaveCount(1);
  const boxes = await Promise.all(
    [page.getByLabel(invite.email, { exact: true }), page.getByRole("group", { name: invite.role }), page.locator("main form button")].map(
      async (locator) => (await locator.boundingBox())!,
    ),
  );
  for (const box of boxes.slice(1)) expect(Math.abs(box.x - boxes[0].x)).toBeLessThan(2);
  expect(boxes[0].y).toBeLessThan(boxes[1].y);
  expect(boxes[1].y).toBeLessThan(boxes[2].y);
}

function freshAddress(tag: string) {
  return `invitert-${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin reaches «Brukere og roller», is told about a bad address and sends an Invitation", async ({
      page,
    }) => {
      if (vp.text200) {
        await page.addInitScript(() => {
          document.addEventListener("DOMContentLoaded", () => {
            const style = document.createElement("style");
            style.textContent = "html { font-size: 200% !important; }";
            document.head.appendChild(style);
          });
        });
      }
      await loginByApi(page, vp.role);
      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.users }).click();
      await expect(page).toHaveURL(/\/admin\/brukere$/);
      await expect(page.getByRole("heading", { level: 1, name: users.title })).toBeVisible();
      await expect(page.getByRole("navigation", { name: nb.navigation.breadcrumb })).toContainText(nb.homes.adminArea);
      await expect(page.getByRole("radio", { name: invite.roles.lecturer })).toBeChecked();
      await expectOneColumnWithOnePrimary(page);
      await expectAccessible(page, vp.phone);

      // A bad address: the invalid state with its reason, and nothing sent.
      const email = page.getByLabel(invite.email, { exact: true });
      await email.fill("kari");
      await page.getByRole("button", { name: invite.submit }).click();
      await expect(email).toHaveAttribute("aria-invalid", "true");
      await expect(email).toHaveAccessibleDescription(nb.auth.login.errors.emailNoAt);
      await expect(email).toBeFocused();
      await expect(page.getByText(/Invitasjonen er sendt/)).toHaveCount(0);
      await expectAccessible(page, vp.phone);

      // The reason clears as the address is typed, not on blur.
      const address = freshAddress(vp.name.replace(/\W+/g, ""));
      await email.fill(address);
      await expect(email).not.toHaveAttribute("aria-invalid", "true");

      await page.getByRole("radio", { name: invite.roles.admin }).check();
      await page.getByRole("button", { name: invite.submit }).click();
      const line = page.getByText(invite.sent(address, invite.roles.admin, 14));
      await expect(line).toBeFocused();
      await expect(email).toHaveValue("");
      await expectAccessible(page, vp.phone);
    });
  });
}

test.describe("mail", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("the Invitation mail reaches the address with its link", async ({ page }) => {
    await loginByApi(page, "admin");
    await page.goto("/admin/brukere");
    const address = freshAddress("mail");
    const before = await latestMail(page, address);
    await page.getByLabel(invite.email, { exact: true }).fill(address);
    await page.getByRole("button", { name: invite.submit }).click();
    await expect(page.getByText(invite.sent(address, invite.roles.lecturer, 14))).toBeFocused();

    const mail = await nextMail(page, address, before);
    expect(mail.subject).toBe("Invitasjon til ØL-spillet");
    expect(mail.text.startsWith("ØL-spillet")).toBe(true);
    expect(mail.text).toContain("som Faglærer");
    expect(mail.text).toMatch(/https?:\/\/\S+\/invitasjon#[A-Za-z0-9_-]{20,}/);
  });
});

test.describe("failure", () => {
  test("a send that fails says so beside the button and keeps the address", async ({ page }) => {
    await loginByApi(page, "admin");
    await page.goto("/admin/brukere");
    // Only the send: the Invitation list on the same page (Story 3.10) reads the same path.
    await page.route("**/api/admin/invitations", (route) =>
      route.request().method() === "POST" ? route.fulfill({ status: 500, body: "" }) : route.continue(),
    );
    const address = freshAddress("failure");
    const email = page.getByLabel(invite.email, { exact: true });
    await email.fill(address);
    await page.getByRole("button", { name: invite.submit }).click();
    await expect(page.getByText(invite.failed)).toBeVisible();
    await expect(email).toHaveValue(address);
    await expect(page.getByText(/Invitasjonen er sendt/)).toHaveCount(0);
  });
});

test.describe("result line", () => {
  test("the result line goes as soon as the role or the address changes (Issue #74)", async ({ page }) => {
    await loginByApi(page, "admin");
    await page.goto("/admin/brukere");
    // The answer of a send, without storing an Invitation: this test is about the form only.
    await page.route("**/api/admin/invitations", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      const body = route.request().postDataJSON() as { email: string; role: string };
      await route.fulfill({
        status: 201,
        json: { id: "x", email: body.email, role: body.role, expires_at: "2026-12-02T12:00:00Z", valid_days: 14 },
      });
    });
    const email = page.getByLabel(invite.email, { exact: true });
    const sent = page.getByText(/Invitasjonen er sendt/);

    await email.fill("kari@example.com");
    await page.getByRole("button", { name: invite.submit }).click();
    await expect(sent).toBeFocused();
    await page.getByRole("radio", { name: invite.roles.admin }).check();
    await expect(sent).toHaveCount(0);

    await email.fill("ola@example.com");
    await page.getByRole("button", { name: invite.submit }).click();
    await expect(sent).toBeFocused();
    await email.pressSequentially("n");
    await expect(sent).toHaveCount(0);
  });
});

test.describe("not an Admin", () => {
  test("a Lecturer gets the permission-denied page and no form", async ({ page }) => {
    await loginByApi(page, "lecturer");
    await page.goto("/admin/brukere");
    await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
    await expect(page.getByLabel(invite.email, { exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: invite.submit })).toHaveCount(0);
  });
});
