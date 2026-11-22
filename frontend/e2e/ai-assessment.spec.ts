import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, test } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/** The Student's «KI-vurdering» (Story 12.2, FR-54, FR-55, FR-61, FR-80, NFR-6, UX-DR5, UX-DR66):
 * not ready, switched off, ready, incomplete and failed at 320, 360 and 1440 px with axe, each
 * starting with the disclosure; ready lists each item's computed result or AI step and points in
 * words and the weighted total, with no pass or fail and no letter; incomplete names the items
 * without a score and shows no total. These use stand-ins with the api's shapes; the job, the
 * scores and the total are `backend/tests/assessment/test_assess.py`. The last test runs on the
 * stack with no stand-in: a fresh Class game, the test handed in, Hjem's «KI-vurdering» link and
 * the not-ready line.
 *
 * Story 12.3 (FR-34, FR-54, FR-81, UX-DR66, UX-DR69): at 360 and 1440 px with axe, an item's
 * written feedback under its score with «KI-generert, kan ta feil:» and the Student's own words as
 * a quotation, the note where feedback was left out, and «Ikke kontrollert med en Kontrolltest.»
 * while the Scoring guide is not checked; the validation and regeneration are
 * `backend/tests/assessment/test_feedback.py`.
 *
 * Story 12.4 (FR-55, AD-8): on the stack, the open Hjem says «KI-vurderingen er klar.» before
 * its Lenke once the assessment job marks the assessment ready, without a reload, at 320 and
 * 1440 px with axe; the step, the notice and the mail are `backend/tests/assessment/
 * test_notices.py`. */
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const CSRF = { "X-Requested-With": "olspillet" };
const copy = nb.assessment.student;
const STATE = "[data-assessment-state]";

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const NONE = { items: [], unassessed: [], total: null, total_max: null, checked: false };
const CHOICE = {
  id: "flervalg-forklaring",
  number: 1,
  type: "choice",
  title: "Utkast: Hva forklarer svingningene best?",
  wording: null,
  weight: 20,
  points: 20,
  computed: { result: "right", criteria: [] },
  ai: null,
};
const TABLE = {
  id: "tabell-annen-bransje",
  number: 2,
  type: "table",
  title: "Utkast: Fyll inn lageret for bakeriet.",
  wording: null,
  weight: 30,
  points: 15,
  computed: {
    result: "partly",
    criteria: [
      { code: "B1", met: true, explanation: "Hver rad stemmer med raden over, pluss inn og minus ut." },
      { code: "B2", met: false, explanation: "Uke 3: 12 + 25 − 20 = 17, svaret er 15." },
    ],
  },
  ai: null,
};
const LONG = {
  id: "langsvar-forsinkelse",
  number: 3,
  type: "long",
  title: "Utkast: Forklar hvorfor ordrene svinger mer oppover i kjeden.",
  wording: null,
  weight: 20,
  points: 15,
  computed: null,
  ai: { assessed: true, step: 3, top: 4, label: "Utkast: godt", feedback: null, feedback_dropped: false },
};
const ADAPTED_TEXT = "Utkast: I uke 7 av Klassespillet var du Grossist og bestilte 16 enheter. Forklar hva du la vekt på.";
const ADAPTED = {
  id: "tilpasset-eget-spill",
  number: 4,
  type: "adapted",
  title: ADAPTED_TEXT,
  wording: { text: ADAPTED_TEXT, ai_generated: false, llm_call_id: null },
  weight: 30,
  points: 7.5,
  computed: null,
  ai: { assessed: true, step: 1, top: 4, label: "Utkast: svakt", feedback: null, feedback_dropped: false },
};
const READY = { state: "ready", items: [CHOICE, TABLE, LONG, ADAPTED], unassessed: [], total: 57.5, total_max: 100, checked: false };
const QUOTE = "Hvert ledd bestiller på det det ser, ikke på kundenes etterspørsel";
const AFTER = ", men svaret forklarer ikke kriteriet F5 (Utkast: kriterium 5).";
const FEEDBACK = {
  ai_generated: true,
  text: `Du skriver «${QUOTE}»${AFTER}`,
  parts: [
    { kind: "text", text: "Du skriver " },
    { kind: "quote", text: QUOTE },
    { kind: "text", text: AFTER },
  ],
};
const WITH_FEEDBACK = {
  ...READY,
  items: [
    CHOICE,
    TABLE,
    { ...LONG, ai: { ...LONG.ai, feedback: FEEDBACK } },
    { ...ADAPTED, ai: { ...ADAPTED.ai, feedback_dropped: true } },
  ],
};
const INCOMPLETE = {
  state: "incomplete",
  items: [CHOICE, TABLE, LONG, { ...ADAPTED, points: null, ai: { assessed: false, step: null, top: 4, label: null } }],
  unassessed: [4],
  total: null,
  total_max: null,
  checked: false,
};

/** The Student's page with the api's answer stood in. */
async function standIn(page: Page, answer: { status: number; json: unknown }) {
  await loginByApi(page, "student");
  await page.route(`**/api/me/class-sessions/${SESSION}/test/assessment`, (route) => route.fulfill(answer));
  await page.goto(`/ki-vurdering/${SESSION}`);
}

/** The disclosure comes first, and no view says pass, fail, grade letter or «Bestått». */
async function startsWithTheDisclosure(page: Page) {
  const main = page.getByRole("main");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
  await expect(main.locator("[data-disclosure]")).toHaveText(copy.disclosure);
  const text = await main.locator(STATE).innerText();
  expect(text.indexOf(copy.disclosure)).toBe(0);
  expect(text).not.toMatch(/Bestått|Ikke bestått|Karakter [A-F]|Veiledende bokstav/u);
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("not ready: the disclosure, then «kommer innen ett døgn»; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: { state: "not_ready", ...NONE } });
      await startsWithTheDisclosure(page);
      await expect(page.locator(STATE)).toHaveAttribute("data-assessment-state", "not_ready");
      await expect(page.getByRole("main")).toContainText(copy.notReady);
      await expect(page.locator("[data-item], [data-total]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("switched off: the Faglærer's line; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: { state: "switched_off", ...NONE } });
      await startsWithTheDisclosure(page);
      await expect(page.getByRole("main")).toContainText(copy.switchedOff);
      await expect(page.locator("[data-item], [data-total]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("ready: each item's result or step and points in words, then the weighted total; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: READY });
      await startsWithTheDisclosure(page);
      const items = page.locator("[data-item]");
      await expect(items).toHaveCount(4);
      await expect(items.nth(0).getByRole("heading", { level: 3 })).toHaveText(`Oppgave 1 · ${nb.tests.individual.types.choice}`);
      await expect(items.nth(0).locator("[data-score]")).toHaveText(copy.computed.right);
      await expect(items.nth(0).locator("[data-points]")).toHaveText("20 av 20 poeng");
      await expect(items.nth(1).locator("[data-score]")).toHaveText(copy.computed.partly);
      await expect(items.nth(1)).toContainText(`${copy.criterionNotMet}: Uke 3: 12 + 25 − 20 = 17, svaret er 15.`);
      await expect(items.nth(2).locator("[data-score]")).toHaveText("KI-vurdering: 3 av 4 (Utkast: godt)");
      await expect(items.nth(3).locator("[data-points]")).toHaveText("7,5 av 30 poeng");
      await expect(items.nth(3)).toContainText(ADAPTED_TEXT);
      await expect(page.locator("[data-total]")).toContainText("Vektet sum: 57,5 av 100 poeng");
      await expect(page.locator("[data-total]")).toContainText(copy.totalNote);
      await expectAccessible(page, vp.phone);
    });

    test("incomplete: the items without a score named, and no total; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: INCOMPLETE });
      await startsWithTheDisclosure(page);
      await expect(page.getByRole("main")).toContainText(copy.incomplete("4"));
      await expect(page.locator("[data-item]").nth(3).locator("[data-score]")).toHaveText(copy.notAssessed);
      await expect(page.locator("[data-item]").nth(3).locator("[data-points]")).toHaveText(copy.notAssessed);
      await expect(page.locator("[data-total]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });

    test("failed: the computed scores are in the Studentrapport; no items, no total; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: { state: "failed", ...NONE } });
      await startsWithTheDisclosure(page);
      await expect(page.getByRole("main")).toContainText(copy.failed);
      await expect(page.locator("[data-item], [data-total]")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
    });
  });
}

for (const vp of VIEWPORTS.filter((each) => each.width !== 320)) {
  test.describe(`feedback, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("feedback quotes the Student's words under the score; a dropped one leaves a note; the unchecked notice; axe passes", async ({ page }) => {
      await standIn(page, { status: 200, json: WITH_FEEDBACK });
      await startsWithTheDisclosure(page);
      await expect(page.locator("[data-unchecked]")).toHaveText(copy.unchecked);
      const items = page.locator("[data-item]");
      const feedback = items.nth(2).locator("[data-feedback]");
      await expect(feedback).toHaveAttribute("data-ai-generated", "true");
      expect((await feedback.innerText()).startsWith(copy.feedbackPrefix)).toBe(true);
      await expect(feedback.locator("q[data-quote]")).toHaveText(QUOTE);
      await expect(feedback).toContainText("kriteriet F5 (Utkast: kriterium 5)");
      // Under the item's score, not above it.
      const score = await items.nth(2).locator("[data-score]").boundingBox();
      const box = await feedback.boundingBox();
      expect(box!.y).toBeGreaterThan(score!.y);
      // No feedback on a computed item; the note in place of the left-out one.
      await expect(items.nth(0).locator("[data-feedback]")).toHaveCount(0);
      await expect(items.nth(3).locator("[data-feedback]")).toHaveCount(0);
      await expect(items.nth(3).locator("[data-feedback-dropped]")).toHaveText(copy.feedbackDropped);
      await expectAccessible(page, vp.phone);
    });

    test("a checked Scoring guide shows no unchecked notice", async ({ page }) => {
      await standIn(page, { status: 200, json: { ...WITH_FEEDBACK, checked: true } });
      await expect(page.locator("[data-item]")).toHaveCount(4);
      await expect(page.locator("[data-unchecked]")).toHaveCount(0);
    });
  });
}

test("another Student's session shows the permission-denied page", async ({ page }) => {
  await standIn(page, { status: 403, json: { error: { code: "forbidden", message: "x", fields: {} } } });
  await expect(page.getByRole("heading", { level: 1 })).not.toHaveText(copy.title);
  await expect(page.locator(STATE)).toHaveCount(0);
});

test("live: the handed-in test puts «KI-vurdering» on Hjem, which is not ready before the Testfrist", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  const [student] = game.students;
  const request = student!.context.request;
  const page = await student!.context.newPage();
  // Before the hand-in Hjem has no «KI-vurdering» link.
  const done = await request.post(`/api/dev/class-sessions/${game.sessionId}/replay-done`, { headers: CSRF });
  expect(done.status()).toBe(204);
  await page.goto("/hjem");
  const main = page.getByRole("main");
  await expect(main.getByRole("region", { name: nb.homes.student.steps })).toBeVisible();
  await expect(main.getByRole("link", { name: copy.link, exact: true })).toHaveCount(0);

  const testPath = `/api/me/class-sessions/${game.sessionId}/test`;
  expect((await request.post(testPath, { headers: CSRF })).status()).toBe(201);
  expect((await request.post(`${testPath}/submit`, { headers: CSRF })).status()).toBe(200);
  await page.reload();
  await main.getByRole("link", { name: copy.link, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/ki-vurdering/${game.sessionId}$`));
  await expect(page.locator(STATE)).toHaveAttribute("data-assessment-state", "not_ready");
  await expect(page.locator("[data-disclosure]")).toHaveText(copy.disclosure);
  await expect(page.getByRole("main")).toContainText(copy.notReady);
  await page.close();
});

test("live: a ready assessment puts «KI-vurderingen er klar.» on the open Hjem without a reload (Story 12.4)", async ({
  browser,
  lecturerSession,
}) => {
  test.slow(); // an Invitation through the worker, a Class session, a lock, an assessment job
  const game = await liveClassGame(browser, lecturerSession, 1, { aiMode: "rule_based" });
  const [student] = game.students;
  const request = student!.context.request;
  const page = await student!.context.newPage();
  await page.setViewportSize({ width: 320, height: 640 });
  expect((await request.post(`/api/dev/class-sessions/${game.sessionId}/replay-done`, { headers: CSRF })).status()).toBe(204);
  const testPath = `/api/me/class-sessions/${game.sessionId}/test`;
  expect((await request.post(testPath, { headers: CSRF })).status()).toBe(201);
  expect((await request.post(`${testPath}/submit`, { headers: CSRF })).status()).toBe(200);
  await page.goto("/hjem");
  const main = page.getByRole("main");
  await expect(main.getByRole("link", { name: copy.link, exact: true })).toBeVisible();
  await expect(main.getByText(copy.readyOnHjem)).toHaveCount(0);

  // The Test-deadline lock, then the close of this attempt: `worker-batch` assesses it on the mock
  // provider, and the ready run's `user:<id>` event reads Hjem again.
  expect((await request.post(`/api/dev/class-sessions/${game.sessionId}/lock-test`, { headers: CSRF })).status()).toBe(200);
  expect((await request.post(`/api/dev/class-sessions/${game.sessionId}/test/close`, { headers: CSRF })).status()).toBe(204);
  await expect(main.getByText(copy.readyOnHjem, { exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(main.locator("[data-assessment-ready]")).toContainText(copy.link);
  await expectAccessible(page, true);
  await page.setViewportSize({ width: 1440, height: 900 });
  await expectAccessible(page, false);

  await main.getByRole("link", { name: copy.link, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/ki-vurdering/${game.sessionId}$`));
  await expect(page.locator(STATE)).toHaveAttribute("data-assessment-state", "ready");
  await page.close();
});
