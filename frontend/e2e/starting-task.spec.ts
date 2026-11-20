import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** The Startoppgave (Story 6.3, FR-85, UX-DR63, UX-DR70), on the local stack as the demo Student.
 * Scoring, storing once, resuming, the version pin and `progress` are the api's, pinned by
 * `backend/tests/starting_task/test_starting_task.py`; a locked game needs the Start date, so here
 * the Starting task routes answer from a small in-test stand-in with the api's shapes and two of
 * the migration's version 1 items, and the demo Class is never changed. The wrong, right, final-question
 * and done states are checked at 320, 360 and 1440 px. */
const copy = nb.games.startingTask;
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed777e";

type Term = { sign: 1 | -1; value: number };
type Item = {
  id: string;
  prompt: string;
  hint: string | null;
  column: string;
  rows: { label: string; value: number }[];
  asked_label: string;
  terms: Term[];
};

const ITEMS: Item[] = [
  {
    id: "to-ship",
    prompt: "Hvor mange enheter skal Grossisten sende i alt denne uka?",
    hint: "Å sende = Restordre før + Ordre inn",
    column: "Uke 11",
    rows: [
      { label: "Restordre før", value: 9 },
      { label: "Ordre inn", value: 8 },
    ],
    asked_label: "Å sende",
    terms: [
      { sign: 1, value: 9 },
      { sign: 1, value: 8 },
    ],
  },
  {
    id: "position",
    prompt: "Regn posisjonen for én Uke.",
    hint: "Posisjon = Lager − Restordre + På vei",
    column: "Uke 11",
    rows: [
      { label: "Lager", value: 0 },
      { label: "Restordre", value: 13 },
      { label: "På vei", value: 16 },
    ],
    asked_label: "Posisjon",
    terms: [
      { sign: 1, value: 0 },
      { sign: -1, value: 13 },
      { sign: 1, value: 16 },
    ],
  },
];

/** The stand-in: answers kept per item (the first wins), the final choice, and the bodies sent. */
async function withTask(page: Page, answered: Record<string, number> = {}) {
  const answers = { ...answered };
  let final: string | null = null;
  const sent: unknown[] = [];
  const state = () => ({
    version: 1,
    items: ITEMS.map(({ terms, ...item }) => {
      const answer = answers[item.id];
      const expected = terms.reduce((sum, t) => sum + t.sign * t.value, 0);
      return {
        ...item,
        result: answer === undefined ? null : { answer, correct: answer === expected, expected, terms },
      };
    }),
    played_before: final,
    done: final !== null,
  });
  const base = `**/api/me/games/${GAME_ID}/starting-task`;
  await page.route(base, (route) => route.fulfill({ json: state() }));
  await page.route(`${base}/answers`, (route) => {
    const body = route.request().postDataJSON();
    sent.push(body);
    answers[body.item_id] ??= body.answer;
    return route.fulfill({ json: state() });
  });
  await page.route(`${base}/final`, (route) => {
    const body = route.request().postDataJSON();
    sent.push(body);
    final ??= body.choice;
    return route.fulfill({ json: state() });
  });
  return Object.assign(sent, { done: () => final !== null });
}

function myGame(done: () => boolean) {
  return {
    id: GAME_ID,
    number: 17,
    role: "wholesaler",
    seats: [
      { role: "factory", holder: "ai", name: null, mine: false },
      { role: "distributor", holder: "ai", name: null, mine: false },
      { role: "wholesaler", holder: "student", name: "Demo Student", mine: true },
      { role: "retailer", holder: "ai", name: null, mine: false },
    ],
    briefing_first: !done(),
    rules: {
      order_delay: 2,
      shipping_delay: 2,
      production_delay: 2,
      guided_weeks: 4,
      holding_cost: "0.50",
      backorder_cost: "1.00",
    },
  };
}

/** Hjem with one locked Class session holding the demo Student's game; `briefing_first` follows
 * the stand-in, as the api's follows `progress`. */
async function withHjem(page: Page, done: () => boolean) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const game = myGame(done);
    const item = {
      id: "01a1f8ee-33b9-75e6-9502-79db27b37c00",
      class_id: klass.id,
      class_name: klass.name,
      number: 1,
      start_at: "2026-11-17T09:00:00Z",
      play_deadline: "2026-12-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      game,
      steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, j) => ({
        step,
        state: j === 0 ? "current" : "locked",
      })),
    };
    await route.fulfill({ response, json: { items: [item] } });
  });
  await page.route(`**/api/me/games/${GAME_ID}`, (route) => route.fulfill({ json: myGame(done) }));
}

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("wrong, right, final question and done, each in words and accessible", async ({ page }) => {
      await loginByApi(page, "student");
      const sent = await withTask(page);
      await page.goto(`/spill/${GAME_ID}/startoppgave`);
      const main = page.getByRole("main");
      await expect(main.getByRole("heading", { level: 1 })).toHaveText(copy.title);
      await expect(main.getByText(copy.lead)).toBeVisible();
      await expect(main.getByText(copy.demoData, { exact: true })).toHaveCount(1);

      // Wrong.
      const toShip = main.getByRole("textbox", { name: "Å sende" });
      await expect(toShip).toHaveAttribute("inputmode", "numeric");
      await toShip.fill("12");
      await main.getByRole("button", { name: copy.send }).click();
      const wrong = main.getByText("Ikke riktig. Svaret er 17: 9 + 8.");
      await expect(wrong).toBeVisible();
      await expect(wrong).toBeFocused();
      await expect(main.getByRole("table", { name: "Uke 11" }).first().getByRole("cell", { name: "12" })).toBeVisible();
      await expectAccessible(page, vp.phone);

      // Right.
      await main.getByRole("textbox", { name: "Posisjon" }).fill("3");
      await main.getByRole("button", { name: copy.send }).click();
      await expect(main.getByText("Riktig. Svaret er 3: 0 − 13 + 16.")).toBeVisible();
      // Final question.
      const group = main.getByRole("group", { name: copy.final.question });
      await expect(group.getByRole("radio")).toHaveCount(3);
      await expect(main.getByRole("button", { name: copy.final.skip })).toBeVisible();
      await expectAccessible(page, vp.phone);

      await group.getByText(copy.final.choices.no).click();
      await main.getByRole("button", { name: copy.send }).click();
      const done = main.getByText(copy.done);
      await expect(done).toBeVisible();
      await expect(done).toBeFocused();
      await expect(main.getByText(copy.startsFromHome)).toBeVisible();
      // The page link at the top and the primary button under the done line both lead to Hjem.
      await expect(main.getByRole("link", { name: copy.toHome })).toHaveCount(2);
      await expect(main.getByRole("link", { name: copy.toHome }).last()).toHaveClass(/(^|\s)bg-ink(\s|$)/);
      await expectAccessible(page, vp.phone);
      expect([...sent]).toEqual([
        { item_id: "to-ship", answer: 12 },
        { item_id: "position", answer: 3 },
        { choice: "no" },
      ]);
    });
  });
}

test("a field that is not a whole number says so on leaving it and on the button", async ({ page }) => {
  await loginByApi(page, "student");
  const sent = await withTask(page);
  await page.goto(`/spill/${GAME_ID}/startoppgave`);
  const main = page.getByRole("main");
  const field = main.getByRole("textbox", { name: "Å sende" });
  for (const bad of ["abc", "1,5"]) {
    await field.fill(bad);
    await field.blur();
    await expect(main.getByRole("alert")).toHaveText(copy.notWhole);
    await expect(field).toHaveAttribute("aria-invalid", "true");
  }
  await field.fill("");
  await main.getByRole("button", { name: copy.send }).click();
  await expect(main.getByRole("alert")).toHaveText(copy.notWhole);
  await expect(field).toBeFocused();
  // The error goes once the field holds a whole number; nothing was sent meanwhile.
  await field.fill("17");
  await expect(main.getByRole("alert")).toHaveCount(0);
  expect([...sent]).toEqual([]);
});

test("by keyboard alone, and resuming at the first unanswered item", async ({ page }) => {
  await loginByApi(page, "student");
  const sent = await withTask(page, { "to-ship": 17 });
  await page.goto(`/spill/${GAME_ID}/startoppgave`);
  const main = page.getByRole("main");
  // The answered item shows its result; the open one is next.
  await expect(main.getByText("Riktig. Svaret er 17: 9 + 8.")).toBeVisible();
  await expect(main.getByRole("textbox")).toHaveCount(1);
  await main.getByRole("textbox", { name: "Posisjon" }).focus();
  await page.keyboard.type("4");
  await page.keyboard.press("Enter");
  await expect(main.getByText("Ikke riktig. Svaret er 3: 0 − 13 + 16.")).toBeFocused();
  // Skipping without a choice finishes too.
  await main.getByRole("button", { name: copy.final.skip }).focus();
  await page.keyboard.press("Enter");
  await expect(main.getByText(copy.done)).toBeFocused();
  expect([...sent]).toEqual([{ item_id: "position", answer: 4 }, { choice: "skipped" }]);
});

test("sending with no choice asks for one or a skip", async ({ page }) => {
  await loginByApi(page, "student");
  const sent = await withTask(page, { "to-ship": 17, position: 3 });
  await page.goto(`/spill/${GAME_ID}/startoppgave`);
  const main = page.getByRole("main");
  await main.getByRole("button", { name: copy.send }).click();
  await expect(main.getByRole("alert")).toHaveText(copy.final.none);
  expect([...sent]).toEqual([]);
});

test("a game that is not the Student's shows the permission-denied page", async ({ page }) => {
  await loginByApi(page, "student");
  await page.goto(`/spill/${GAME_ID}/startoppgave`); // the real api: no game of the demo Student
  await expect(page.getByText(nb.access.denied)).toBeVisible();
  await expect(page.getByRole("heading", { name: copy.title })).toHaveCount(0);
});

test("once done, Hjem at once shows the rules as a Lenke, not «Les reglene»", async ({ page }) => {
  await loginByApi(page, "student");
  const sent = await withTask(page, { "to-ship": 17, position: 3 });
  await withHjem(page, sent.done);
  await page.goto("/hjem");
  const main = page.getByRole("main");
  // In-app navigation, so Hjem's earlier read stays in the cache: Hjem → briefing → Startoppgave.
  await main.getByRole("link", { name: nb.homes.student.readRules }).click();
  await main.getByRole("link", { name: nb.games.briefing.done }).click();
  await main.getByRole("button", { name: copy.final.skip }).click();
  await main.getByRole("link", { name: copy.toHome }).last().click();
  await expect(page).toHaveURL(/\/hjem$/);
  // Within the cache's 30 s, Hjem reads again: the briefing no longer comes first.
  await expect(main.getByRole("link", { name: nb.homes.student.rulesLink })).toBeVisible();
  await expect(main.getByRole("link", { name: nb.homes.student.readRules })).toHaveCount(0);
});
