import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { effectLine, levelLabel, type OfferedLevel } from "../src/modules/sessions/choices";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** Choosing KI-modus, Innsatsnivå and Debrief-modus on the Klasseøkt (Story 5.5, FR-15, FR-16,
 * FR-78, UX-DR12, UX-DR48, UX-DR49), on the local stack, where the seeded mock model config is the
 * default. Each test makes a fresh Lecturer and Class through the api. The save rules, the offered
 * levels and the lock are pinned through the routes by `backend/tests/sessions/test_ai_mode.py`;
 * here the screen. */
const copy = nb.sessions;
const c = copy.choices;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id as string;
}

async function stored(lecturer: Page, id: string) {
  return (await lecturer.request.get(`/api/class-sessions/${id}`)).json();
}

/** The session as the server would answer in another state; the api tests pin the real one. */
async function answerWith(lecturer: Page, id: string, changes: Record<string, unknown>) {
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), ...changes } });
  });
}

const group = (page: Page, name: string) => page.getByRole("group", { name, exact: true });

test("the choices take effect on save: Rule-based hides the Effort level, Personal debrief is stored", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const before = await stored(lecturer, id);
  expect(before.ai_mode).toBe("llm");
  const levels = before.effort_levels as OfferedLevel[];
  expect(levels.length).toBeGreaterThan(0);
  await lecturer.goto(`/klasseokter/${id}`);

  const aiMode = group(lecturer, c.aiMode);
  await expect(aiMode.getByRole("radio", { name: c.llm })).toBeChecked();
  await expect(aiMode).toHaveAccessibleDescription(c.aiScope);
  // The offered levels from the model config, the default chosen, each with one effect line.
  const effort = group(lecturer, c.effortLevel);
  for (const level of levels) {
    const radio = effort.getByRole("radio", { name: levelLabel(level) });
    await expect(radio).toHaveAccessibleDescription(effectLine(level));
    if (level.name === before.effort_level) await expect(radio).toBeChecked();
  }
  // Each AI player type's description, from the players module.
  await lecturer.getByText(c.aboutRuleBased).click();
  await expect(lecturer.getByText(/forankring og justering/)).toBeVisible();

  // By keyboard: the arrow key moves the choice to Rule-based; the Effort level hides.
  await aiMode.getByRole("radio", { name: c.llm }).focus();
  await lecturer.keyboard.press("ArrowRight");
  await expect(aiMode.getByRole("radio", { name: c.ruleBased })).toBeChecked();
  await expect(effort).toHaveCount(0);
  const debrief = group(lecturer, c.debriefMode);
  await expect(debrief).toHaveAccessibleDescription(c.groupHelp);
  await debrief.getByText(c.personal, { exact: true }).click();
  await expect(debrief).toHaveAccessibleDescription(c.personalHelp);
  // Nothing is stored before «Lagre Klasseøkt».
  expect((await stored(lecturer, id)).ai_mode).toBe("llm");

  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const after = await stored(lecturer, id);
  expect([after.ai_mode, after.effort_level, after.debrief_mode]).toEqual(["rule_based", null, "personal"]);
  await lecturer.reload();
  await expect(group(lecturer, c.aiMode).getByRole("radio", { name: c.ruleBased })).toBeChecked();
  await expect(group(lecturer, c.debriefMode).getByRole("radio", { name: c.personal })).toBeChecked();

  // Back to LLM players: the default level is chosen again and stored on save.
  await group(lecturer, c.aiMode).getByText(c.llm, { exact: true }).click();
  await expect(group(lecturer, c.effortLevel)).toBeVisible();
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const again = await stored(lecturer, id);
  expect([again.ai_mode, again.effort_level]).toEqual(["llm", before.effort_level]);
});

test("with no default model, «LLM-spillere» is unavailable with the reason beside it", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await answerWith(lecturer, id, {
    ai_mode: "rule_based",
    effort_level: null,
    effort_levels: [],
    llm_unavailable: "no_default_model",
  });
  await lecturer.goto(`/klasseokter/${id}`);
  const aiMode = group(lecturer, c.aiMode);
  const llm = aiMode.getByRole("radio", { name: c.llm });
  await expect(llm).toHaveAttribute("aria-disabled", "true");
  await expect(llm).toHaveAccessibleDescription(c.llmUnavailable);
  await expect(aiMode.getByRole("radio", { name: c.ruleBased })).toBeChecked();
  // A press (forced past Playwright's own aria-disabled check) leaves the choice as it is.
  await aiMode.getByText(c.llm, { exact: true }).click({ force: true });
  await expect(aiMode.getByRole("radio", { name: c.ruleBased })).toBeChecked();
  await expect(group(lecturer, c.effortLevel)).toHaveCount(0);
});

test("LLM players whose provider is not set up are named before the Start date", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await answerWith(lecturer, id, { provider_unavailable: true, effort_levels: [] });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(c.providerUnavailable)).toBeVisible();
  // Rule-based chosen: the warning goes with LLM players.
  await group(lecturer, c.aiMode).getByText(c.ruleBased, { exact: true }).click();
  await expect(lecturer.getByText(c.providerUnavailable)).toHaveCount(0);
});

test("a level the config no longer offers is refused on save with the reason", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer when the level was withdrawn between load and save; the api tests pin it.
  await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
    if (route.request().method() !== "PUT") return route.fallback();
    await route.fulfill({
      status: 422,
      json: {
        error: { code: "invalid_effort_level", message: "x", fields: { effort_level: "not_offered" } },
      },
    });
  });
  await lecturer.goto(`/klasseokter/${id}`);
  await lecturer.getByRole("button", { name: copy.save }).click();
  await expect(lecturer.getByRole("alert").filter({ hasText: c.effortRefused })).toBeVisible();
});

test("a session that has started shows the choices as text, with no control", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const level = ((await stored(lecturer, id)).effort_levels as OfferedLevel[])[0];
  await answerWith(lecturer, id, { locked: true });
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(lecturer.getByText(nb.sessions.lock.pending)).toBeVisible();
  await expect(lecturer.getByRole("radio")).toHaveCount(0);
  await expect(lecturer.getByRole("heading", { name: c.aiMode })).toBeVisible();
  // Under its label, as the other locked values (Issue #109).
  const effort = lecturer.getByRole("group", { name: c.effortLevel });
  await expect(effort.getByRole("heading", { name: c.effortLevel })).toBeVisible();
  await expect(effort.getByText(levelLabel(level), { exact: true })).toBeVisible();
  await expect(lecturer.getByText(c.group, { exact: true })).toBeVisible();
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  // 1280 × 800 at 400 % zoom lays out as 320 × 200 CSS px.
  { name: "400 % zoom", width: 320, height: 200, phone: true },
];

for (const vp of SIZES) {
  test.describe(`the choices, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("pass axe with the Effort level, a description open and an unavailable option", async ({
      page,
      browser,
    }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      await expect(group(lecturer, c.effortLevel)).toBeVisible();
      await lecturer.getByText(c.aboutLlm).click();
      await expectAccessible(lecturer, vp.phone);
      // Each segment is a 44 px target.
      const box = await group(lecturer, c.aiMode).locator("label").first().boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);

      await answerWith(lecturer, id, {
        ai_mode: "rule_based",
        effort_level: null,
        effort_levels: [],
        llm_unavailable: "no_default_model",
      });
      await lecturer.reload();
      await expect(group(lecturer, c.aiMode).getByRole("radio", { name: c.llm })).toHaveAttribute(
        "aria-disabled",
        "true",
      );
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
