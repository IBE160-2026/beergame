import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { gameLine, holderName, movedLine, pickLabel, targetLabel } from "../src/modules/sessions/allocation";
import type { Allocation, AllocationGame } from "../src/modules/sessions/api";
import { osloDayAndTime } from "../src/modules/sessions/dates";
import { roleName } from "../src/modules/sessions/sessions";
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

/** The selected game's Seats as the Lecturer edits them (Story 5.10): each row names its holder. */
async function expectSeats(page: Page, game: AllocationGame) {
  const seats = page.getByRole("region", { name: a.seatsHeading(game.number) });
  for (const seat of game.seats) {
    await expect(seats.locator(`li[data-seat='${seat.role}']`)).toContainText(holderName(seat));
  }
}

const at = (game: AllocationGame, index: number) => ({ game: game.number, seat: game.seats[index] });
const studentIndex = (game: AllocationGame) => game.seats.findIndex((seat) => seat.user_id != null);
const freeIndex = (game: AllocationGame) => game.seats.findIndex((seat) => seat.user_id == null);

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
  await expectSeats(lecturer, first.games[0]);
  // By keyboard to game 2, which has one Student and three KI-spillere.
  await columns(lecturer).first().focus();
  await lecturer.keyboard.press("ArrowRight");
  await expect(columns(lecturer).nth(1)).toBeFocused();
  await expect(columns(lecturer).nth(1)).toHaveAttribute("aria-pressed", "true");
  await expectSeats(lecturer, first.games[1]);
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

  // «Kjør fordeling på nytt» is secondary; it stores a new draft and tells nobody. «Bekreft
  // fordeling» is the primary button while the panel is open (Story 5.9).
  const redraw = lecturer.getByRole("button", { name: a.redraw });
  await expect(redraw).toHaveClass(/bg-paper/);
  await expect(lecturer.getByRole("button", { name: a.confirm })).toHaveClass(/bg-ink/);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveClass(/bg-paper/);
  await redraw.click();
  await expect(lecturer.getByRole("status").filter({ hasText: a.redrawn })).toBeVisible();
  const again = (await storedAllocation(lecturer, id)).draft!;
  expect(again.id).not.toBe(first.id);
  await expectSeats(lecturer, again.games[0]);
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
    await expect(lecturer.getByRole("button", { name: /^Flytt/ })).toHaveCount(0);
    await expect(lecturer.getByText(gameLine((await storedAllocation(lecturer, id)).draft!.games[0]))).toBeVisible();
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
    confirmed: false,
    confirmed_at: null,
    opened: false,
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
      await expectSeats(lecturer, body.draft!.games[99]);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.getByText(a.list, { exact: true }).click();
      await expect(lecturer.getByRole("list", { name: a.heading(100) }).getByRole("listitem")).toHaveCount(100);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.context().close();
    });
  });
}

test("«Bekreft fordeling» commits the draft shown and closes to the confirmed line", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const { id } = await sessionWithStudents(lecturer, 5);
  await lecturer.goto(`/klasseokter/${id}`);
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  const confirm = lecturer.getByRole("button", { name: a.confirm });
  await expect(confirm).toHaveAccessibleDescription(a.noticeLine);
  await confirm.click();
  // The panel closes to the state line, which takes focus; «Lagre Klasseøkt» is primary again.
  const state = lecturer.getByText(a.confirmed, { exact: true });
  await expect(state).toBeFocused();
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveClass(/bg-ink/);
  const stored = await storedAllocation(lecturer, id);
  expect(stored.confirmed).toBe(true);
  // Opened again it shows the confirmed draft, with neither a new draw nor a second confirm.
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  await expectSeats(lecturer, stored.draft!.games[0]);
  // It says it is confirmed, and when (issue 107).
  const when = osloDayAndTime(stored.confirmed_at!);
  await expect(lecturer.getByText(a.confirmedOn(when.day, when.time))).toBeVisible();
  await expect(lecturer.getByText(a.movedNotice)).toBeVisible();
  await expect(lecturer.getByRole("button", { name: a.redraw })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: a.confirm })).toHaveCount(0);
  await expect(lecturer.getByRole("button", { name: copy.save })).toHaveClass(/bg-ink/);
  // Back inside the app, the Lærerhjem names what this session still lacks: its dates, not its
  // allocation (the cached «Venter» was read again).
  const klassName = (await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).class_name as string;
  await lecturer.getByRole("link", { name: nb.homes.lecturerHome }).click();
  await expect(lecturer.getByRole("link", { name: copy.home.lacks(klassName, 1, ["dates"]) })).toBeVisible();
  await lecturer.context().close();
});

test("a draft drawn again meanwhile is shown, not confirmed", async ({ browser, lecturerSession }) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const { id } = await sessionWithStudents(lecturer, 6);
  await lecturer.goto(`/klasseokter/${id}`);
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  // A co-owner runs it again in another tab.
  const redrawn = await lecturer.request.post(`/api/class-sessions/${id}/allocation/redraw`, { headers: CSRF });
  const current = ((await redrawn.json()) as Allocation).draft!;
  const confirm = lecturer.getByRole("button", { name: a.confirm });
  await confirm.click();
  await expect(lecturer.getByRole("main").getByRole("alert")).toHaveText(a.changed);
  await expectSeats(lecturer, current.games[0]);
  expect((await storedAllocation(lecturer, id)).confirmed).toBe(false);
  // The next press confirms what is now shown.
  await confirm.click();
  await expect(lecturer.getByText(a.confirmed, { exact: true })).toBeFocused();
  expect((await storedAllocation(lecturer, id)).draft!.id).toBe(current.id);
  await lecturer.context().close();
});

test("a removed Student's cell reads apart, and the selected frame is 1 px until the keyboard focuses it", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const { id } = await sessionWithStudents(lecturer, 0);
  const body = hundredGames();
  body.draft!.games = body.draft!.games.slice(0, 3);
  body.draft!.games[0].seats[1] = { ...body.draft!.games[0].seats[1], name: null };
  await lecturer.route(`**/api/class-sessions/${id}/allocation`, (route) => route.fulfill({ json: body }));
  await lecturer.goto(`/klasseokter/${id}`);
  await opener(lecturer).click();
  await expect(heading(lecturer, 3)).toBeFocused();
  const removed = lecturer.locator("svg rect[data-seat='removed']");
  await expect(removed).toHaveCount(1);
  await expect(removed).toHaveAttribute("stroke-dasharray", "3 2");
  await expect(removed).toHaveAttribute("fill", "var(--color-paper)");
  await expect(lecturer.locator("svg rect[data-seat='student']").first()).toHaveAttribute(
    "fill",
    "var(--color-bar-base)",
  );
  await expect(lecturer.getByText(a.removed, { exact: false })).toBeVisible();
  // A click selects with the 1 px frame; the keyboard shows the 3 px focus ring.
  await columns(lecturer).nth(1).click();
  const frame = lecturer.locator("svg rect[data-frame]");
  await expect(frame).toHaveAttribute("stroke-width", "1");
  await lecturer.keyboard.press("ArrowRight");
  await expect(columns(lecturer).nth(2)).toBeFocused();
  await expect(frame).toHaveAttribute("stroke-width", "3");
  await lecturer.context().close();
});

/** The Seat a move filled, as the draft holds it afterwards: the moved Student in the target's Role. */
const landed = (from: ReturnType<typeof at>, to: ReturnType<typeof at>) => ({
  game: to.game,
  seat: { ...to.seat, user_id: from.seat.user_id, name: from.seat.name },
});

const statusLine = (page: Page, text: string) => page.getByRole("status").filter({ hasText: text });

test("a Student is moved and two swapped by keyboard, before and after the confirmation", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const { id } = await sessionWithStudents(lecturer, 5);
  await lecturer.goto(`/klasseokter/${id}`);
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  const first = (await storedAllocation(lecturer, id)).draft!;

  // Game 1's first Student is picked with Space; the pick is said, and the button now cancels it.
  const from = at(first.games[0], studentIndex(first.games[0]));
  await lecturer.getByRole("button", { name: pickLabel(from) }).press("Space");
  await expect(statusLine(lecturer, a.picked(holderName(from.seat), roleName(from.seat.role), 1))).toBeVisible();
  await expect(lecturer.getByRole("button", { name: a.cancelPick })).toBeFocused();
  // Game 2 is chosen in the chart with the arrow keys; its free Seat takes the Student.
  await columns(lecturer).first().focus();
  await lecturer.keyboard.press("ArrowRight");
  const to = at(first.games[1], freeIndex(first.games[1]));
  await lecturer.getByRole("button", { name: targetLabel(from, to) }).press("Enter");
  await expect(statusLine(lecturer, movedLine(from, to))).toBeVisible();
  // Focus is on the changed row; the draft keeps its id under the next revision.
  await expect(lecturer.getByRole("button", { name: pickLabel(landed(from, to)) })).toBeFocused();
  const second = (await storedAllocation(lecturer, id)).draft!;
  expect([second.id, second.revision]).toEqual([first.id, 2]);
  await expectSeats(lecturer, second.games[1]);

  // A swap back across games, game 1 chosen with ←.
  const mover = landed(from, to);
  await lecturer.getByRole("button", { name: pickLabel(mover) }).press("Enter");
  await columns(lecturer).nth(1).focus();
  await lecturer.keyboard.press("ArrowLeft");
  const other = at(second.games[0], studentIndex(second.games[0]));
  await lecturer.getByRole("button", { name: targetLabel(mover, other) }).press("Enter");
  await expect(statusLine(lecturer, movedLine(mover, other))).toBeVisible();
  await expect(lecturer.getByRole("button", { name: pickLabel(landed(mover, other)) })).toBeFocused();
  expect((await storedAllocation(lecturer, id)).draft!.revision).toBe(3);

  // «Bekreft fordeling» commits the edited draft.
  await lecturer.getByRole("button", { name: a.confirm }).click();
  await expect(lecturer.getByText(a.confirmed, { exact: true })).toBeFocused();
  const confirmed = await storedAllocation(lecturer, id);
  expect([confirmed.confirmed, confirmed.draft!.revision]).toEqual([true, 3]);

  // After it, a swap still works until the lock; the Class games follow (the api tests pin them).
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  const when = osloDayAndTime(confirmed.confirmed_at!);
  await expect(lecturer.getByText(a.confirmedOn(when.day, when.time))).toBeVisible();
  const c = confirmed.draft!;
  const from3 = at(c.games[0], studentIndex(c.games[0]));
  await lecturer.getByRole("button", { name: pickLabel(from3) }).click();
  await columns(lecturer).nth(1).click();
  const to3 = at(c.games[1], studentIndex(c.games[1]));
  await lecturer.getByRole("button", { name: targetLabel(from3, to3) }).click();
  await expect(statusLine(lecturer, movedLine(from3, to3))).toBeVisible();
  const after = await storedAllocation(lecturer, id);
  expect([after.confirmed, after.draft!.revision]).toEqual([true, 4]);
  await expect(lecturer.getByText(a.confirmedOn(when.day, when.time))).toBeVisible();
  await lecturer.context().close();
});

test("a confirmed allocation opened read-only says it is confirmed, and when", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const { id } = await sessionWithStudents(lecturer, 3);
  const drawn = (await (
    await lecturer.request.post(`/api/class-sessions/${id}/allocation`, { headers: CSRF })
  ).json()) as Allocation;
  const confirmed = await lecturer.request.post(`/api/class-sessions/${id}/allocation/confirm`, {
    data: { draft_id: drawn.draft!.id, revision: drawn.draft!.revision },
    headers: CSRF,
  });
  expect(confirmed.ok()).toBe(true);
  const stored = await storedAllocation(lecturer, id);
  // An Assistant lecturer's view of it, as the server answers it (the api tests pin the real one).
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), can_manage: false } });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await opener(lecturer).click();
  await expect(heading(lecturer, 1)).toBeFocused();
  const when = osloDayAndTime(stored.confirmed_at!);
  await expect(lecturer.getByText(a.confirmedOn(when.day, when.time))).toBeVisible();
  await expect(lecturer.getByText(gameLine(stored.draft!.games[0]))).toBeVisible();
  await expect(lecturer.getByRole("button", { name: /^Flytt/ })).toHaveCount(0);
  await expect(lecturer.getByText(a.movedNotice)).toHaveCount(0);
  await lecturer.context().close();
});

for (const vp of SIZES) {
  test(`moving by tap at ${vp.name}: labelled buttons, no drag, focus back, and axe passes`, async ({
    browser,
    lecturerSession,
  }) => {
    const lecturer = await lecturerPage(browser, lecturerSession, vp);
    const { id } = await sessionWithStudents(lecturer, 5);
    await lecturer.goto(`/klasseokter/${id}`);
    await opener(lecturer).click();
    await expect(heading(lecturer, 2)).toBeFocused();
    const first = (await storedAllocation(lecturer, id)).draft!;
    await expectAccessible(lecturer, vp.phone);
    const from = at(first.games[0], studentIndex(first.games[0]));
    await lecturer.getByRole("button", { name: pickLabel(from) }).click();
    // Picked: each other Seat of game 1 holds a Student, so each offers a swap naming both.
    await expect(lecturer.getByRole("button", { name: /^Bytt / })).toHaveCount(3);
    await expectAccessible(lecturer, vp.phone);
    await columns(lecturer).nth(1).click();
    const to = at(first.games[1], freeIndex(first.games[1]));
    await lecturer.getByRole("button", { name: targetLabel(from, to) }).click();
    await expect(lecturer.getByRole("button", { name: pickLabel(landed(from, to)) })).toBeFocused();
    await expectAccessible(lecturer, vp.phone);
    await lecturer.context().close();
  });
}

test("a move on a draft changed meanwhile is refused, and the current draft is shown", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const { id } = await sessionWithStudents(lecturer, 5);
  await lecturer.goto(`/klasseokter/${id}`);
  await opener(lecturer).click();
  await expect(heading(lecturer, 2)).toBeFocused();
  const first = (await storedAllocation(lecturer, id)).draft!;
  const from = at(first.games[0], studentIndex(first.games[0]));
  await lecturer.getByRole("button", { name: pickLabel(from) }).click();
  // A co-owner swaps two other Students in another tab meanwhile.
  const elsewhere = await lecturer.request.post(`/api/class-sessions/${id}/allocation/move`, {
    data: {
      draft_id: first.id,
      revision: first.revision,
      from_game: 1,
      from_role: first.games[0].seats.filter((seat) => seat.user_id != null)[1].role,
      to_game: 2,
      to_role: first.games[1].seats[studentIndex(first.games[1])].role,
    },
    headers: CSRF,
  });
  expect(elsewhere.ok()).toBe(true);
  const current = ((await elsewhere.json()) as Allocation).draft!;
  await lecturer.getByRole("button", { name: /^Bytt / }).first().click();
  await expect(lecturer.getByRole("main").getByRole("alert")).toHaveText(a.changed);
  // The pick is cleared and the panel shows the draft as it is now; nothing else moved.
  await expect(lecturer.getByRole("button", { name: a.cancelPick })).toHaveCount(0);
  await expectSeats(lecturer, current.games[0]);
  expect((await storedAllocation(lecturer, id)).draft!.revision).toBe(2);
  await lecturer.context().close();
});
