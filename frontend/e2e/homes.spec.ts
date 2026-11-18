import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { DEMO_USERS, type DemoRole, loginByApi } from "./support/auth";

const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640 },
  { name: "360 px", width: 360, height: 740 },
  { name: "1440 px", width: 1440, height: 900 },
];

const TITLE: Record<DemoRole, string> = {
  admin: nb.homes.adminArea,
  lecturer: nb.homes.lecturerHome,
  adminLecturer: nb.homes.lecturerHome,
  student: nb.homes.home,
};

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual(
    [],
  );
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(scrolls).toBe(false);
}

async function expectSession(page: Page, role: DemoRole) {
  const banner = page.getByRole("banner");
  await expect(banner.getByText(DEMO_USERS[role].name, { exact: true })).toBeVisible();
  await expect(banner.getByRole("button", { name: nb.auth.session.logout })).toBeVisible();
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    for (const role of ["admin", "lecturer", "student"] as const) {
      test(`${role} opens the product and lands on their own home`, async ({ page }) => {
        await loginByApi(page, role);
        await page.goto("/");
        await expect(page).toHaveURL(new RegExp(`${DEMO_USERS[role].home}$`));
        await expect(page.getByRole("heading", { level: 1, name: TITLE[role] })).toBeVisible();
        await expectSession(page, role);
        // No global navigation bar (UX-DR77), and no link to a home that is not theirs. The
        // Admin-område lists its own pages (Story 3.7).
        await expect(page.locator("nav")).toHaveCount(0);
        const links = role === "admin" ? [nb.admin.sections.users] : [];
        await expect(page.getByRole("main").getByRole("link")).toHaveText(links);
        await expectAccessible(page);
      });
    }

    test("a Lecturer opening the Admin-område is refused, with a link to the Lærerhjem", async ({ page }) => {
      await loginByApi(page, "lecturer");
      await page.goto("/admin");
      await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
      await expect(page).toHaveURL(/\/admin$/);
      await expect(page.getByRole("heading", { name: nb.homes.adminArea })).toHaveCount(0);
      await expectSession(page, "lecturer");
      await expectAccessible(page);
      await page.getByRole("link", { name: nb.navigation.toLecturerHome }).click();
      await expect(page).toHaveURL(/\/laererhjem$/);
    });

    test("an address that matches no page shows «Fant ikke siden.»", async ({ page }) => {
      await loginByApi(page, "student");
      await page.goto("/finnes-ikke");
      await expect(page.getByRole("heading", { level: 1, name: nb.access.notFound })).toBeVisible();
      await expect(page.getByRole("link", { name: nb.navigation.toHome })).toHaveAttribute("href", "/hjem");
      await expectAccessible(page);
    });
  });
}

test("Admin and Lecturer lands on the Lærerhjem, and one login reaches both homes", async ({ page }) => {
  await loginByApi(page, "adminLecturer");
  await page.goto("/");
  await expect(page).toHaveURL(/\/laererhjem$/);
  await expect(page.getByRole("heading", { level: 1, name: nb.homes.lecturerHome })).toBeVisible();
  await page.getByRole("link", { name: nb.navigation.toAdminArea }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { level: 1, name: nb.homes.adminArea })).toBeVisible();
  await expectSession(page, "adminLecturer");
  await expectAccessible(page);
  await page.getByRole("link", { name: nb.navigation.toLecturerHome }).click();
  await expect(page).toHaveURL(/\/laererhjem$/);
});

test("each User refused a page gets a link to their own home", async ({ browser }) => {
  const cases: [DemoRole, string, string][] = [
    ["admin", "/laererhjem", nb.navigation.toAdminArea],
    ["admin", "/hjem", nb.navigation.toAdminArea],
    ["student", "/admin", nb.navigation.toHome],
    ["student", "/laererhjem", nb.navigation.toHome],
    ["lecturer", "/hjem", nb.navigation.toLecturerHome],
    ["adminLecturer", "/hjem", nb.navigation.toLecturerHome],
  ];
  await Promise.all(
    cases.map(async ([role, path, link]) => {
      const context = await browser.newContext();
      try {
        const page = await context.newPage();
        await loginByApi(page, role);
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
        await expect(page.getByRole("main").getByRole("link")).toHaveText([link]);
        await expect(page).toHaveTitle(`${nb.access.denied} – ${nb.product.name}`);
      } finally {
        await context.close();
      }
    }),
  );
});

test("a visitor who is not logged in goes from a home to «Logg inn», with the way back", async ({ page }) => {
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/logg-inn\?neste=%2Fadmin$/);
  // A first visit is not an ended session.
  await expect(page.getByText(nb.auth.login.sessionExpired)).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1, name: nb.auth.login.title })).toBeVisible();
});

test("the not-found page links a visitor who is not logged in to «Logg inn»", async ({ page }) => {
  await page.goto("/finnes-ikke");
  await expect(page.getByRole("heading", { level: 1, name: nb.access.notFound })).toBeVisible();
  await expect(page.getByRole("link", { name: nb.navigation.toLogin })).toHaveAttribute("href", "/logg-inn");
});

test("the product name stands at the same height on «Logg inn» and on a home (Issue #68)", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  const top = async () => (await page.getByRole("banner").getByText(nb.product.name).boundingBox())!.y;
  await page.goto("/logg-inn");
  const onLogin = await top();
  await loginByApi(page, "lecturer");
  await page.goto("/laererhjem");
  await expect(page.getByRole("heading", { level: 1, name: nb.homes.lecturerHome })).toBeVisible();
  expect(Math.abs((await top()) - onLogin)).toBeLessThan(1);
});
