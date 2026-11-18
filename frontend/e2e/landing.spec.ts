import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { DEMO_USERS, loginByApi } from "./support/auth";

/** The Landing and «Be om lærertilgang» (Story 3.13, UX-DR61, UX-DR70, UX-DR75, NFR-6), on the
 * local stack. Each submitting test uses its own fresh address and dismisses its request again. */
const landing = nb.landing;
const form = nb.accessRequest;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

/** Widths from the story. 400 % zoom on a 1280 × 1024 screen is a 320 × 256 CSS-pixel viewport. */
const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "400 % zoom", width: 320, height: 256, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`)).toEqual([]);
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(scrolls).toBe(false);
}

function freshAddress(tag: string) {
  return `laerer-${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/** Dismiss the open request of `name` as the Admin, in a context of its own, so the test leaves
 * the shared list as it found it. */
async function dismissRequestOf(page: Page, name: string) {
  const context = await page.context().browser()!.newContext({ baseURL: "http://127.0.0.1:8080" });
  const admin = await context.newPage();
  try {
    await loginByApi(admin, "admin");
    const list = await (await admin.request.get("/api/admin/access-requests", { params: { limit: 100 } })).json();
    const mine = list.items.find((item: { name: string }) => item.name === name);
    expect(mine).toBeTruthy();
    const response = await admin.request.post(`/api/admin/access-requests/${mine.id}/dismiss`, {
      headers: { "X-Requested-With": "olspillet" },
    });
    expect(response.status()).toBe(204);
  } finally {
    await context.close();
  }
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("a visitor reads the Landing", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("banner")).toHaveText(nb.product.name);
      const headline = page.getByRole("heading", { level: 1, name: landing.headline });
      const lead = page.getByText(landing.lead);
      const request = page.getByRole("link", { name: landing.requestAccess });
      const login = page.getByRole("link", { name: landing.login, exact: true });
      const table = page.getByRole("table", { name: landing.seat.caption });
      for (const locator of [headline, lead, request, login, table]) await expect(locator).toBeVisible();
      await expect(request).toHaveAttribute("href", "/laerertilgang");
      await expect(login).toHaveAttribute("href", "/logg-inn");
      // One Seat in the Veiledede uker: weeks 1–4 as columns, tabular figures, «Demodata».
      await expect(table.getByRole("columnheader")).toHaveText([landing.seat.week, "1", "2", "3", "4"]);
      await expect(table.getByRole("rowheader")).toHaveText([
        nb.terms.incomingOrder,
        nb.terms.incomingDelivery,
        nb.terms.netInventory,
        nb.terms.supplyLine,
        landing.seat.yourOrder,
      ]);
      await expect(table).toHaveCSS("font-variant-numeric", "lining-nums tabular-nums");
      const demo = page.getByText(landing.seat.demoData, { exact: true });
      await expect(demo).toBeVisible();
      await expect(demo).toHaveCSS("color", "rgb(94, 111, 130)");
      await expect(page.getByText(landing.seat.classCurves)).toBeVisible();
      if (vp.phone) {
        // One column: headline, lead, buttons, Seat table, top to bottom.
        const boxes = await Promise.all([headline, lead, request, table].map(async (l) => (await l.boundingBox())!));
        for (let i = 1; i < boxes.length; i++) expect(boxes[i].y).toBeGreaterThan(boxes[i - 1].y);
      } else {
        // Laptop: the lead stands to the right of the headline.
        const [h, l] = await Promise.all([headline.boundingBox(), lead.boundingBox()]);
        expect(l!.x).toBeGreaterThan(h!.x + h!.width);
        await expect(headline).toHaveCSS("font-size", "48px");
      }
      await expectAccessible(page);
    });

    test("the request form shows its reasons and passes axe", async ({ page }) => {
      await page.goto("/laerertilgang");
      await expect(page.getByRole("heading", { level: 1, name: form.title })).toBeVisible();
      await page.getByLabel(form.institution).fill("a@b");
      await page.getByRole("button", { name: form.submit }).click();
      await expect(page.getByLabel(form.name)).toBeFocused();
      await expect(page.getByText(form.errors.nameEmpty)).toBeVisible();
      await expect(page.getByText(form.errors.emailEmpty)).toBeVisible();
      await expect(page.getByText(form.errors.institutionInvalid)).toBeVisible();
      await expectAccessible(page);
    });
  });
}

test("a visitor asks for lecturer access and the page confirms the Admin will answer", async ({ page }) => {
  const name = `Lærer ${Date.now()}`;
  await page.goto("/");
  await page.getByRole("link", { name: landing.requestAccess }).click();
  await expect(page).toHaveURL(/\/laerertilgang$/);
  await page.getByLabel(form.name).fill(name);
  await page.getByLabel(form.email).fill(freshAddress("skjema"));
  await page.getByLabel(form.institution).fill("Universitetet i Sørøst-Norge");
  await page.getByRole("button", { name: form.submit }).click();
  await expect(page.getByText(form.sent)).toBeFocused();
  await expect(page.getByRole("link", { name: form.toLanding })).toHaveAttribute("href", "/");
  await dismissRequestOf(page, name);
});

test("a refused request keeps what was typed and says why", async ({ page }) => {
  await page.goto("/laerertilgang");
  await page.getByLabel(form.name).fill("Ola Nordmann");
  await page.getByLabel(form.email).fill("ola@example.com");
  await page.getByLabel(form.institution).fill("USN");
  for (const [status, code, message] of [
    [429, "rate_limited", form.rateLimited],
    [500, "server_error", form.failed],
  ] as const) {
    await page.route("**/api/auth/access-request", (route) =>
      route.fulfill({ status, json: { error: { code, message: "x", fields: {} } } }),
    );
    await page.getByRole("button", { name: form.submit }).click();
    await expect(page.getByRole("main").getByRole("alert")).toHaveText(message);
    await expect(page.getByLabel(form.name)).toHaveValue("Ola Nordmann");
    await page.unrouteAll();
  }
});

test("a logged-in User who opens the root address goes to their own home", async ({ page }) => {
  await loginByApi(page, "admin");
  await page.goto("/");
  await expect(page).toHaveURL(new RegExp(`${DEMO_USERS.admin.home}$`));
});
