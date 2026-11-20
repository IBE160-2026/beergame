import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { gameLine } from "../src/modules/sessions/allocation";
import type { Allocation, AllocationGame } from "../src/modules/sessions/api";
import { expectAccessible, freshClass, lecturerPage, test } from "./support/classes";

/** «Fordeling» on the Klasseøkt (Story 5.8, FR-20, NFR-6, UX-DR50, UX-DR75), on the local stack.
 * Each test makes a fresh Class with Students registered by hand through the api. The draw, the
 * stored draft, the lock and the refusals are pinned by `backend/tests/sessions/test_allocation.py`;
 * here the screen. */
const copy = nb.sessions;
const a = copy.allocation;
const CSRF = { "X-Requested-With": "olspillet" };

/** A fresh Class with `students` registered by hand, and a Class session of it. */
async function sessionWithStudents(
  lecturer: Page,
  students: number,
): Promise<{ id: string; names: string[]; classId: string }> {
  const klass = await freshClass(lecturer);
  const names: string[] = [];
  for (let i = 0; i < students; i++) {
    const name = `Student${i + 1} ${klass.name}`;
    const registered = await lecturer.request.post(`/api/classes/${klass.id}/roster/manual`, {
      data: { email: `fordeling-${klass.name}-${i}@example.com`, name },
      headers: CSRF,
    });
    expect(registered.ok()).toBe(true);
    names.push(name);
  }
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return { id: (await created.json()).id as string, names, classId: klass.id };
}

async function storedAllocation(lecturer: Page, id: string): Promise<Allocation> {
  return (await lecturer.request.get(`/api/class-sessions/${id}/allocation`)).json();
}

const opener = (page: Page) => page.getByRole("button", { name: a.open });
const heading = (page: Page, games: number) => page.getByRole("heading", { name: a.heading(games) });
const columns = (page: Page) => page.locator("svg g[role='button']");

test("opening «Fordeling» draws a draft, shows it, and running it again replaces it", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, {
    width: 1440,
    height: 900,
  });
  const { id, names, classId } = await sessionWithStudents(lecturer, 5);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(a.notConfirmed)).toBeVisible();
  expect((await storedAllocation(lecturer, id)).draft).toBeNull();

  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  await expect(lecturer.getByText(a.lead(5))).toBeVisible();
  const first = (await storedAllocation(lecturer, id)).draft!;
  expect(first.revision).toBe(1);
  await expect(columns(lecturer)).toHaveCount(2);
  // Game 1 is selected: its line names its four Students in the stored draft.
  await expect(lecturer.getByText(gameLine(first.games[0]))).toBeVisible();
  // By keyboard to game 2, which has one Student and three KI-spillere.
  await columns(lecturer).first().focus();
  await lecturer.keyboard.press("ArrowRight");
  await expect(columns(lecturer).nth(1)).toBeFocused();
  await expect(columns(lecturer).nth(1)).toHaveAttribute("aria-pressed", "true");
  await expect(lecturer.getByText(gameLine(first.games[1]))).toBeVisible();
  expect(gameLine(first.games[1]).split(a.aiPlayer).length - 1).toBe(3);

  // «Vis som liste»: every game with its names; every Student is there once.
  await lecturer.getByText(a.list, { exact: true }).click();
  const list = lecturer.getByRole("list", { name: a.heading(2) });
  await expect(list.getByRole("listitem")).toHaveCount(2);
  for (const name of names) await expect(list.getByText(name)).toHaveCount(1);

  // Closing and opening again shows the same stored draft.
  await lecturer.getByRole("button", { name: a.close }).click();
  await expect(opener(lecturer)).toBeFocused();
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeVisible();
  expect((await storedAllocation(lecturer, id)).draft!.id).toBe(first.id);

  // «Kjør fordeling på nytt» is secondary; it stores a new draft and tells nobody.
  const redraw = lecturer.getByRole("button", { name: a.redraw });
  await expect(redraw).toHaveClass(/bg-paper/);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveClass(/bg-ink/);
  await redraw.click();
  await expect(lecturer.getByRole("status").filter({ hasText: a.redrawn })).toBeVisible();
  const again = (await storedAllocation(lecturer, id)).draft!;
  expect(again.id).not.toBe(first.id);
  await expect(lecturer.getByText(gameLine(again.games[0]))).toBeVisible();
  await expect(lecturer.getByText(a.noticeLine)).toBeVisible();

  // A Student who registers after the draw is not in it: the panel says so after a reload.
  const late = await lecturer.request.post(`/api/classes/${classId}/roster/manual`, {
    data: { email: `fordeling-sen-${Date.now()}@example.com`, name: "Sen Student" },
    headers: CSRF,
  });
  expect(late.ok()).toBe(true);
  await lecturer.reload();
  await opener(lecturer).click();
  await expect(lecturer.getByText(`${a.missing(1)} ${a.missingRedraw}`)).toBeVisible();
  await expect(lecturer.getByText(a.emptySeats)).toBeVisible();
  await lecturer.context().close();
});

test("with no registered Student the block says so and offers no preview", async ({ browser, lecturerSession }) => {
  const lecturer = await lecturerPage(browser, lecturerSession, {
    width: 1440,
    height: 900,
  });
  const { id } = await sessionWithStudents(lecturer, 0);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(a.nobody)).toBeVisible();
  await expect(opener(lecturer)).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: /Bekreft/ })).toHaveCount(0);
  await lecturer.context().close();
});

for (const [who, changes] of [
  ["an Assistant", { can_manage: false }],
  ["a session that has started", { locked: true }],
] as const) {
  test(`${who} reads the stored draft with no redraw`, async ({ browser, lecturerSession }) => {
    const lecturer = await lecturerPage(browser, lecturerSession, {
      width: 1440,
      height: 900,
    });
    const { id } = await sessionWithStudents(lecturer, 3);
    const drawn = await lecturer.request.post(`/api/class-sessions/${id}/allocation`, { headers: CSRF });
    expect(drawn.ok()).toBe(true);
    // The session as the server answers in that state; the api tests pin the real one.
    await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
      if (route.request().method() !== "GET") return route.fallback();
      const response = await route.fetch();
      await route.fulfill({
        response,
        json: { ...(await response.json()), ...changes },
      });
    });
    let posts = 0;
    lecturer.on("request", (request) => {
      if (request.method() === "POST" && request.url().includes("/allocation")) posts += 1;
    });
    await lecturer.goto(`/klasseokter/${id}`);
    await opener(lecturer).click();
    await expect(heading(lecturer, 1)).toBeFocused();
    await expect(lecturer.getByRole("button", { name: a.redraw })).toHaveCount(0);
    expect(posts).toBe(0);
    await lecturer.context().close();
  });
}

/** 100 Class games of four, the last with one Student, for the width checks. */
function hundredGames(): Allocation {
  const games: AllocationGame[] = Array.from({ length: 100 }, (_, i) => ({
    number: i + 1,
    seats: (["factory", "distributor", "wholesaler", "retailer"] as const).map((role, r) => {
      const held = i < 99 || r === 3;
      return {
        role,
        user_id: held ? `00000000-0000-0000-0000-${String(i * 4 + r).padStart(12, "0")}` : null,
        name: held ? `Navn ${i * 4 + r}` : null,
      };
    }),
  }));
  return {
    registered_count: 397,
    missing_count: 0,
    draft: {
      id: "00000000-0000-0000-0000-00000000aaaa",
      revision: 1,
      drawn_at: new Date().toISOString(),
      games,
    },
  };
}

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`Fordelingsforhåndsvisning, ${vp.name}`, () => {
    test("100 games scroll in their own region, the list reflows, and axe passes", async ({
      browser,
      lecturerSession,
    }) => {
      const lecturer = await lecturerPage(browser, lecturerSession, vp);
      const { id } = await sessionWithStudents(lecturer, 0);
      const body = hundredGames();
      await lecturer.route(`**/api/class-sessions/${id}/allocation`, (route) => route.fulfill({ json: body }));
      await lecturer.goto(`/klasseokter/${id}`);
      await opener(lecturer).click();
      await expect(heading(lecturer, 100)).toBeFocused();
      const region = lecturer.getByRole("group", { name: a.chartLabel });
      const widths = await region.evaluate((el) => ({
        scroll: el.scrollWidth,
        client: el.clientWidth,
      }));
      expect(widths.scroll).toBeGreaterThan(widths.client);
      // The region takes focus with a visible ring, and the columns are reachable by keyboard.
      await lecturer.getByRole("radio", { name: a.chart }).focus();
      await lecturer.keyboard.press("Tab");
      await expect(region).toBeFocused();
      await expect(region).toHaveCSS("outline-style", "solid");
      await lecturer.keyboard.press("Tab");
      await expect(columns(lecturer).first()).toBeFocused();
      await lecturer.keyboard.press("End");
      await expect(columns(lecturer).last()).toBeFocused();
      await expect(lecturer.getByText(gameLine(body.draft!.games[99]))).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
      await lecturer.getByText(a.list, { exact: true }).click();
      await expect(lecturer.getByRole("list", { name: a.heading(100) }).getByRole("listitem")).toHaveCount(100);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}
