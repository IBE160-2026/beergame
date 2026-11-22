import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { osloDateText } from "../src/modules/sessions/dates";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** «KI-vurdering» on the Klasseøkt (Story 12.1, FR-61, UX-DR12, UX-DR49), on the local stack: on by
 * default, switched off with «Lagre Klasseøkt», and pinned by the Test-deadline lock, which the
 * local-only `POST /api/dev/class-sessions/{id}/lock-test` runs at once. The api's rules (the
 * refusal after the Testfrist, the Assistant's 403, the sweep) are pinned by
 * `backend/tests/sessions/test_ai_assessment_switch.py`. */
const copy = nb.assessment.switchBlock;
const CSRF = { "X-Requested-With": "olspillet" };
const DAY = 24 * 60 * 60 * 1000;

async function newSession(lecturer: Page): Promise<{ id: string; ai_mode: string }> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return created.json();
}

/** A Class session switched off and pinned by the Test-deadline lock; the pin time is returned. */
async function pinnedOff(lecturer: Page): Promise<{ id: string; pinnedAt: string }> {
  const session = await newSession(lecturer);
  const [start_at, play_deadline, debrief_deadline, test_deadline] = [3, 17, 20, 27].map((d) =>
    new Date(Date.now() + d * DAY).toISOString(),
  );
  const saved = await lecturer.request.put(`/api/class-sessions/${session.id}`, {
    data: { ai_mode: session.ai_mode, ai_assessment: false, dates: { start_at, play_deadline, debrief_deadline, test_deadline } },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  const locked = await lecturer.request.post(`/api/dev/class-sessions/${session.id}/lock-test`, { headers: CSRF });
  expect(locked.status()).toBe(200);
  const read = await (await lecturer.request.get(`/api/class-sessions/${session.id}`)).json();
  return { id: session.id, pinnedAt: read.ai_assessment.pinned_at };
}

const block = (page: Page) => page.locator("[data-ai-assessment]");
const toggle = (page: Page) => block(page).getByRole("switch");

test("on by default, switched off with «Lagre Klasseøkt» and read back", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const { id } = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByRole("heading", { name: copy.title, exact: true })).toBeVisible();
  // The state in words beside the track, read with the name: never by colour alone.
  await expect(toggle(lecturer)).toHaveAccessibleName(`${copy.title} ${copy.on}`);
  await expect(toggle(lecturer)).toHaveAttribute("aria-checked", "true");
  await expect(toggle(lecturer)).toHaveAccessibleDescription(`${copy.lead} ${copy.help}`);
  await expect(block(lecturer).getByText(copy.open)).toBeVisible();

  await toggle(lecturer).click();
  await expect(toggle(lecturer)).toHaveAccessibleName(`${copy.title} ${copy.off}`);
  await expect(toggle(lecturer)).toHaveAttribute("aria-checked", "false");
  await lecturer.getByRole("button", { name: nb.sessions.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
  expect(stored.ai_assessment.enabled).toBe(false);
  await lecturer.reload();
  await expect(toggle(lecturer)).toHaveAttribute("aria-checked", "false");
});

test("pinned at the Testfrist it stands as text, and the api refuses a change", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const { id, pinnedAt } = await pinnedOff(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByText(copy.pinned(osloDateText(pinnedAt)))).toBeVisible();
  await expect(block(lecturer).getByText(copy.off, { exact: true })).toBeVisible();
  await expect(block(lecturer).getByText(copy.help)).toBeVisible();
  await expect(toggle(lecturer)).toHaveCount(0);
  const refused = await lecturer.request.put(`/api/class-sessions/${id}`, {
    data: { ai_mode: "rule_based", ai_assessment: true },
    headers: CSRF,
  });
  expect(refused.status()).toBe(409);
  expect((await refused.json()).error).toMatchObject({ code: "ai_assessment_pinned", fields: { ai_assessment: "pinned" } });
});

test("an Assistant reads the value as text", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const { id } = await newSession(lecturer);
  // The server's answer to an Assistant lecturer (`ai_assessment.change` is the owners' only).
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: { ...body, can_manage: false, ai_assessment: { ...body.ai_assessment, can_change: false } },
    });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByText(copy.on, { exact: true })).toBeVisible();
  await expect(toggle(lecturer)).toHaveCount(0);
  await lecturer.unrouteAll({ behavior: "ignoreErrors" });
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of SIZES) {
  test.describe(`KI-vurdering, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("on, off and locked pass axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const { id } = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await expect(toggle(lecturer)).toHaveAttribute("aria-checked", "true");
      await toggle(lecturer).scrollIntoViewIfNeeded();
      const box = await toggle(lecturer).boundingBox();
      expect(box && box.height >= 44 && box.width >= 44).toBe(true);
      await expectAccessible(lecturer, vp.phone);
      await toggle(lecturer).click();
      await expect(toggle(lecturer)).toHaveAttribute("aria-checked", "false");
      await expectAccessible(lecturer, vp.phone);

      const pinned = await pinnedOff(lecturer);
      await lecturer.goto(`/klasseokter/${pinned.id}`);
      await expect(block(lecturer).getByText(copy.pinned(osloDateText(pinned.pinnedAt)))).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
