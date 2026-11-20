import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { DEMO_USERS, loginByApi } from "./support/auth";

/** «Revisjonslogg» in the Admin-område (Story 3.12, FR-3, FR-5, NFR-6, UX-DR75), on the local
 * stack. The database is shared between runs, so each test makes and finds its own rows by a
 * unique name; the empty states and an action of a later epic are answered by the test. */
const copy = nb.admin.audit;
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

type Viewport = { name: string; width: number; height: number; phone: boolean };

const VIEWPORTS: Viewport[] = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
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
    [...document.querySelectorAll<HTMLElement>("main a, main button, main input, main select")]
      .filter((el) => el.offsetParent !== null)
      .map((el) => ({ name: el.id || el.textContent?.trim(), ...el.getBoundingClientRect().toJSON() }))
      .filter((b) => b.height < 44 || b.width < 44),
  );
  expect(small).toEqual([]);
}

/** The actor filter lists everyone who ever acted, and the local database keeps every run's fresh
 * Lecturers: thousands of options, over which axe alone took 13 s. The real answer is fetched and
 * cut to the system and the demo Users, so the page's size does not grow with the runs. */
async function demoActorsOnly(page: Page) {
  const demo = new Set<string>(Object.values(DEMO_USERS).map((user) => user.name));
  await page.route("**/api/admin/audit/actors", async (route) => {
    try {
      const response = await route.fetch();
      const { items } = (await response.json()) as { items: { id: string | null; name: string | null }[] };
      await route.fulfill({ response, json: { items: items.filter((a) => a.id === null || demo.has(a.name ?? "")) } });
    } catch {
      // A test that does not read the filter can end with this answer in flight.
    }
  });
}

const tag = () => `${Date.now()}${Math.floor(Math.random() * 1e6)}`;
const actorFilter = (page: Page) => page.getByLabel(copy.filters.actor, { exact: true });
const actionFilter = (page: Page) => page.getByLabel(copy.filters.action, { exact: true });
const sinceField = (page: Page) => page.getByLabel(copy.filters.since, { exact: true });
const untilField = (page: Page) => page.getByLabel(copy.filters.until, { exact: true });

const event = (n: number, action = "institution.created") => ({
  id: `00000000-0000-7000-8000-00000000000${n}`,
  occurred_at: "2026-11-18T12:01:00Z",
  action,
  actor_id: null,
  actor_name: null,
  targets: [{ key: "institution_id", id: "x", label: `Side ${n}` }],
  change: {},
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the Admin opens «Revisjonslogg» and finds a fresh action with names", async ({ page }) => {
      await demoActorsOnly(page);
      await loginByApi(page, "admin");
      const name = `Revisjon ${tag()}`;
      const created = await page.request.post("/api/admin/institutions", {
        data: { name },
        headers: { "X-Requested-With": "olspillet" },
      });
      expect(created.status()).toBe(201);

      await page.goto("/admin");
      await page.getByRole("link", { name: nb.admin.sections.audit }).click();
      await expect(page).toHaveURL(/\/admin\/revisjonslogg$/);
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();

      await actorFilter(page).selectOption({ label: DEMO_USERS.admin.name });
      // The rows of the actor filter alone stay until the answer to both filters is in: wait for
      // that answer, so the list read below is the filtered one.
      const filtered = page.waitForResponse((r) => {
        const url = new URL(r.url());
        return url.pathname === "/api/admin/audit" && url.searchParams.get("action") === "institution.created";
      });
      await actionFilter(page).selectOption("institution.created");
      expect((await filtered).status()).toBe(200);
      const row = page.locator("tbody tr").filter({ hasText: name });
      await expect(row).toBeVisible();
      await expect(row).toContainText(DEMO_USERS.admin.name);
      await expect(row).toContainText(copy.actions["institution.created"]);
      await expect(row).toContainText(`${copy.fields.name}: ${name}`);
      await expect(row).toContainText(/\d{1,2}\. [a-zæøå]+\.? \d{4} kl\. \d{2}:\d{2}/);
      // Only that action is listed.
      await expect(page.locator("tbody tr").filter({ hasNotText: copy.actions["institution.created"] })).toHaveCount(0);
      await expectAccessible(page, vp.phone);
      await expect(page.locator("main button.bg-ink")).toHaveCount(0);
    });
  });
}

test.describe("filters and states", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("a date range with nothing in it says «Ingen treff.», a reversed one says why", async ({ page }) => {
    const asked: URLSearchParams[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.pathname === "/api/admin/audit") asked.push(url.searchParams);
    });
    await demoActorsOnly(page);
    await loginByApi(page, "admin");
    await page.goto("/admin/revisjonslogg");
    await expect(page.locator("tbody tr").first()).toBeVisible();

    await sinceField(page).fill("2099-01-01");
    const noMatches = page.getByRole("status").filter({ hasText: copy.list.noMatches });
    await expect(noMatches).toBeVisible();
    await expect(page.getByRole("table")).toHaveCount(0);

    await untilField(page).fill("2098-12-31");
    await expect(page.getByText(copy.filters.rangeReversed)).toBeVisible();
    await expect(untilField(page)).toHaveAttribute("aria-invalid", "true");
    // The reversed range is never asked for: the list stays as it was, with no page error.
    await expect(noMatches).toBeVisible();
    await expect(page.getByText(nb.system.pageError)).toHaveCount(0);
    await expectAccessible(page, false);
    // Another filter still applies, with the last valid dates.
    await actionFilter(page).selectOption("role.granted");
    await expect.poll(() => asked.some((q) => q.get("action") === "role.granted")).toBe(true);
    expect(asked.filter((q) => q.get("until") === "2098-12-31")).toEqual([]);
    expect(asked.find((q) => q.get("action") === "role.granted")?.get("since")).toBe("2099-01-01");
    await actionFilter(page).selectOption("");

    await sinceField(page).fill("");
    await untilField(page).fill("");
    await expect(page.getByText(copy.filters.rangeReversed)).toHaveCount(0);
    await expect(page.locator("tbody tr").first()).toBeVisible();
  });

  test("with no events the log says so", async ({ page }) => {
    await page.route("**/api/admin/audit?*", (route) => route.fulfill({ json: { items: [], next_cursor: null } }));
    await page.route("**/api/admin/audit", (route) => route.fulfill({ json: { items: [], next_cursor: null } }));
    await demoActorsOnly(page);
    await loginByApi(page, "admin");
    await page.goto("/admin/revisjonslogg");
    await expect(page.getByRole("status").filter({ hasText: copy.list.empty })).toBeVisible();
    await expectAccessible(page, false);
  });

  test("an action of a later epic renders from its generic fields, by the system", async ({ page }) => {
    const later = {
      ...event(1, "takeover.by_person"),
      targets: [{ key: "seat_id", id: "s", label: null }],
      change: { reason: "absent", role: "lecturer" },
    };
    await page.route("**/api/admin/audit?*", (route) => route.fulfill({ json: { items: [later], next_cursor: null } }));
    await page.route("**/api/admin/audit", (route) => route.fulfill({ json: { items: [later], next_cursor: null } }));
    await loginByApi(page, "admin");
    await page.goto("/admin/revisjonslogg");
    const row = page.locator("tbody tr");
    await expect(row).toContainText("takeover.by_person");
    await expect(row).toContainText(copy.system);
    await expect(row).toContainText(copy.unknown);
    await expect(row).toContainText("reason: absent");
    await expect(row).toContainText(`${copy.fields.role}: ${copy.values.roles.lecturer}`);
    await expect(row).toContainText("18. nov. 2026 kl. 13:01");
  });

  test("«Vis flere hendelser» appends the next page by its cursor", async ({ page }) => {
    const cursors: (string | null)[] = [];
    const answer = (route: import("@playwright/test").Route) => {
      const cursor = new URL(route.request().url()).searchParams.get("cursor");
      cursors.push(cursor);
      return route.fulfill({
        json: cursor ? { items: [event(2)], next_cursor: null } : { items: [event(1)], next_cursor: "neste" },
      });
    };
    await page.route("**/api/admin/audit?*", answer);
    await page.route("**/api/admin/audit", answer);
    await loginByApi(page, "admin");
    await page.goto("/admin/revisjonslogg");
    await expect(page.getByText("Side 1", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: copy.list.more }).click();
    await expect(page.getByText("Side 2", { exact: true })).toBeVisible();
    await expect(page.getByText("Side 1", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: copy.list.more })).toHaveCount(0);
    expect(cursors).toContain("neste");
  });

  test("a failed «Vis flere hendelser» keeps the rows shown and says so", async ({ page }) => {
    const answer = (route: import("@playwright/test").Route) =>
      new URL(route.request().url()).searchParams.get("cursor")
        ? route.fulfill({ status: 500, json: { error: { code: "internal", message: "x", fields: {} } } })
        : route.fulfill({ json: { items: [event(1)], next_cursor: "neste" } });
    await page.route("**/api/admin/audit?*", answer);
    await page.route("**/api/admin/audit", answer);
    await loginByApi(page, "admin");
    await page.goto("/admin/revisjonslogg");
    await page.getByRole("button", { name: copy.list.more }).click();
    await expect(page.getByText(copy.list.moreFailed)).toBeVisible();
    await expect(page.getByText("Side 1", { exact: true })).toBeVisible();
    await expect(page.getByText(nb.system.pageError)).toHaveCount(0);
  });

  test("a Lecturer gets the permission-denied page", async ({ page }) => {
    await loginByApi(page, "lecturer");
    await page.goto("/admin/revisjonslogg");
    await expect(page.getByRole("heading", { level: 1, name: nb.access.denied })).toBeVisible();
    await expect(actionFilter(page)).toHaveCount(0);
  });
});
