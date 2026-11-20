import { type Browser, expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { deadlineText } from "../src/modules/games/home";
import { DEMO_PASSWORD, loginByApi } from "./support/auth";
import { expectAccessible, freshClass, freshLecturerWithAddress, lecturerPage, test } from "./support/classes";

/** Pages that follow changes by themselves (Story 6.4, AD-8, NFR-5, UX-DR78), on the local stack
 * through the proxy. The stream's scope, coalescing, heartbeat and lifetime are pinned by
 * `backend/tests/platform/test_event_stream.py` and the topic map by `src/lib/api/topics.test.ts`;
 * here two live flows end to end, a reconnect and a missed heartbeat. Each live flow makes a fresh
 * Class; the demo Student registered on one is taken off its Roster again. */
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;
const a = nb.sessions.allocation;

/** Wait until the page's event stream has sent `ready`: from then on no change is missed. */
async function untilLive(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-live", "live", { timeout: 10_000 });
}

async function newSession(lecturer: Page, classId: string): Promise<string> {
  const created = await lecturer.request.post(`/api/classes/${classId}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

/** The four dates, days from now, saved through the api; returns the saved Class session. */
async function saveDates(lecturer: Page, sessionId: string, days: number[]) {
  const [start_at, play_deadline, debrief_deadline, test_deadline] = days.map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const session = await (await lecturer.request.get(`/api/class-sessions/${sessionId}`)).json();
  const saved = await lecturer.request.put(`/api/class-sessions/${sessionId}`, {
    data: { ai_mode: session.ai_mode, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  return { next_deadline: { kind: "play" as const, at: play_deadline } };
}

async function studentPage(browser: Browser, email: string): Promise<Page> {
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: 360, height: 740 },
  });
  const login = await context.request.post("/api/auth/login", { data: { email, password: DEMO_PASSWORD }, headers: CSRF });
  expect(login.status()).toBe(200);
  return context.newPage();
}

test("a Lecturer moves the Spillfrist and the Student's open Hjem shows it within 2 s, focus kept", async ({
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1280, height: 800 });
  const klass = await freshClass(lecturer);
  const registered = await lecturer.request.post(`/api/classes/${klass.id}/roster/manual`, {
    data: { email: "student8@example.com", name: "Demo Student 8" },
    headers: CSRF,
  });
  expect(registered.status()).toBe(201);
  const entry = (await registered.json()).id as string;
  let student: Page | undefined;
  try {
    const sessionId = await newSession(lecturer, klass.id);
    const before = await saveDates(lecturer, sessionId, [3, 17, 20, 27]);
    student = await studentPage(browser, "student8@example.com");
    await student.goto("/hjem");
    const main = student.getByRole("main");
    await expect(main.getByText(deadlineText(before)!, { exact: true })).toBeVisible();
    await untilLive(student);
    const logout = student.getByRole("button", { name: nb.auth.session.logout });
    await logout.focus();

    const after = await saveDates(lecturer, sessionId, [3, 18, 21, 28]);
    await expect(main.getByText(deadlineText(after)!, { exact: true })).toBeVisible({ timeout: 2_000 });
    await expect(main.getByText(deadlineText(before)!, { exact: true })).toHaveCount(0);
    await expect(logout).toBeFocused();
  } finally {
    await student?.context().close();
    const removed = await lecturer.request.delete(`/api/classes/${klass.id}/roster/entries/${entry}`, { headers: CSRF });
    expect(removed.status()).toBe(204);
    await lecturer.context().close();
  }
});

test("a co-owner confirms the allocation and the other Lecturer's open Klasseøkt shows it, focus kept", async ({
  page,
  browser,
  lecturerSession,
}) => {
  const lecturer = await lecturerPage(browser, lecturerSession, { width: 1440, height: 900 });
  const klass = await freshClass(lecturer);
  for (let i = 0; i < 3; i++) {
    const registered = await lecturer.request.post(`/api/classes/${klass.id}/roster/manual`, {
      data: { email: `live-${klass.name}-${i}@example.com`, name: `Live${i} ${klass.name}` },
      headers: CSRF,
    });
    expect(registered.ok()).toBe(true);
  }
  const sessionId = await newSession(lecturer, klass.id);
  const coOwner = await freshLecturerWithAddress(page, browser);
  const added = await lecturer.request.post(`/api/classes/${klass.id}/staff/lecturers`, {
    data: { email: coOwner.address },
    headers: CSRF,
  });
  expect(added.status()).toBe(201);

  await lecturer.goto(`/klasseokter/${sessionId}`);
  const opener = lecturer.getByRole("button", { name: a.open });
  await expect(opener).toBeVisible();
  await untilLive(lecturer);
  await opener.focus();

  const drawn = await (await coOwner.page.request.post(`/api/class-sessions/${sessionId}/allocation`, { headers: CSRF })).json();
  const confirmed = await coOwner.page.request.post(`/api/class-sessions/${sessionId}/allocation/confirm`, {
    data: { draft_id: drawn.draft.id, revision: drawn.draft.revision },
    headers: CSRF,
  });
  expect(confirmed.ok()).toBe(true);
  // `session:<id>` is coalesced to one event per 2 s: the confirmation may come at the window's end.
  await expect(lecturer.getByText(a.confirmed, { exact: true })).toBeVisible({ timeout: 4_000 });
  await expect(opener).toBeFocused();
  await coOwner.page.context().close();
  await lecturer.context().close();
});

test("a dropped connection shows «Frakoblet. …», and on return «Tilkoblet igjen.» and Hjem is read again", async ({
  page,
  context,
}) => {
  await loginByApi(page, "student");
  await page.goto("/hjem");
  await expect(page.getByRole("heading", { level: 2, name: /class-of-1994/ })).toBeVisible();
  await untilLive(page);
  await context.setOffline(true);
  await expect(page.getByRole("status").filter({ hasText: nb.system.offline })).toBeVisible();
  const reread = page.waitForResponse((r) => new URL(r.url()).pathname === "/api/me/class-sessions");
  await context.setOffline(false);
  await expect(page.getByRole("status").filter({ hasText: nb.system.reconnected })).toBeVisible();
  expect((await reread).status()).toBe(200);
  await untilLive(page);
});

test("a missed heartbeat marks the page «Sist oppdatert 21:14»", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.clock.install({ time: new Date("2026-11-20T20:14:00Z") });
  await loginByApi(page, "student");
  await page.goto("/hjem");
  await expect(page.getByRole("heading", { level: 2, name: /class-of-1994/ })).toBeVisible();
  await untilLive(page);
  await page.clock.fastForward(25_000);
  const line = page.getByRole("status").filter({ hasText: nb.system.stale });
  await expect(line).toBeVisible();
  await expect(line).toContainText(nb.system.lastUpdated("21:14"));
  await expectAccessible(page, true);
  // The next beat makes it live again, with «Tilkoblet igjen.» (`src/lib/api/live.test.ts`).
});
