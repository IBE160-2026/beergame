import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible } from "./support/classes";

/** «Regler før første ordre» (Story 6.2, FR-84, FR-14, UX-DR63, UX-DR70), on the local stack as
 * the demo Student. `briefing_first` and the rules are the api's, pinned by
 * `backend/tests/sessions/test_student_home.py`; a locked game needs the Start date, so here the
 * server's answers for the demo Student are laid over the real ones and the demo Class is never
 * changed. The screen is checked at 320, 360 and 1440 px. */
const copy = nb.games.briefing;
const home = nb.homes.student;
const GAME_ID = "01a1f8ee-34f2-70af-8800-f79281ed777e";

const RULES = {
  order_delay: 2,
  shipping_delay: 2,
  production_delay: 2,
  guided_weeks: 4,
  holding_cost: "0.50",
  backorder_cost: "1.00",
};

function game(briefingFirst: boolean, rules = RULES, role = "wholesaler") {
  return {
    id: GAME_ID,
    number: 17,
    role,
    seats: [
      { role: "factory", holder: "student", name: "Jonas Berg", mine: role === "factory" },
      { role: "distributor", holder: "ai", name: null, mine: false },
      { role: "wholesaler", holder: "student", name: "Demo Student", mine: role === "wholesaler" },
      { role: "retailer", holder: "ai", name: null, mine: false },
    ],
    briefing_first: briefingFirst,
    rules,
  };
}

/** The demo Student's Class with one locked Class session per game in `found` (number 1, 2, …),
 * on Hjem and on the game route of the first. */
async function withGame(page: Page, ...found: ReturnType<typeof game>[]) {
  await page.route("**/api/me/class-sessions", async (route) => {
    const response = await route.fetch();
    const classes = await (await page.request.get("/api/classes/enrolled")).json();
    const [klass] = classes.items;
    const items = found.map((one, i) => ({
      id: `01a1f8ee-33b9-75e6-9502-79db27b37c0${i}`,
      class_id: klass.id,
      class_name: klass.name,
      number: i + 1,
      start_at: "2026-11-17T09:00:00Z",
      play_deadline: "2026-12-08T13:00:00Z",
      debrief_deadline: null,
      test_deadline: null,
      next_deadline: { kind: "play", at: "2026-12-08T13:00:00Z" },
      obligatory: false,
      lab_hours: [],
      seat_choice_open: false,
      drawn_seat: null,
      game: one,
      steps: ["class_game", "debrief", "quiz", "replay", "test", "report"].map((step, j) => ({
        step,
        state: j === 0 ? "current" : "locked",
      })),
    }));
    await route.fulfill({ response, json: { items } });
  });
  await page.route(`**/api/me/games/${GAME_ID}`, (route) => route.fulfill({ json: found[0] }));
}

// A test that ends on Hjem may leave the overlaid read in flight.
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

    test("the briefing states the rules, one Uke as Demodata, and one primary button", async ({ page }) => {
      await loginByApi(page, "student");
      await withGame(page, game(true));
      await page.goto(`/spill/${GAME_ID}/regler`);
      const main = page.getByRole("main");
      await expect(main.getByRole("heading", { level: 1 })).toHaveText(copy.title);
      // Heading order: one h1, then the sections as h2, nothing deeper.
      await expect(main.getByRole("heading", { level: 2 })).toHaveText([
        copy.goal.title,
        copy.week.title,
        copy.delays.title,
        copy.example.title,
        copy.guided.title,
        copy.together.title,
      ]);
      await expect(main.getByRole("heading", { level: 3 })).toHaveCount(0);
      await expect(main.getByText(copy.goal.text)).toBeVisible();
      await expect(main.getByText(/^Hver enhet på lager koster 0,50 kr per uke\./)).toBeVisible();
      await expect(main.getByText(copy.week.same)).toBeVisible();
      await expect(main.getByText(copy.week.ship)).toBeVisible();
      await expect(main.getByText("Ordren din kommer fram til Distributøren to uker etter at du la den inn.")).toBeVisible();
      await expect(main.getByText(/^De første fire ukene er veiledede uker\./)).toBeVisible();
      await expect(main.getByText(copy.together.continues)).toBeVisible();
      await expect(main.getByText(copy.together.arrange)).toBeVisible();
      const table = main.getByRole("table", { name: copy.example.caption });
      await expect(table.getByRole("rowheader")).toHaveText([
        "Ordre inn",
        "Levering",
        "Sendt",
        "Lager",
        "Restordre",
        "Netto lager",
        "På vei",
      ]);
      await expect(main.getByText(copy.example.demoData, { exact: true })).toBeVisible();
      await expect(table.getByRole("cell", { name: "13", exact: true })).toBeVisible();
      await expect(main.getByText(/^Denne uka: 13 enheter i restordre, hver til 1,00 kr\./)).toBeVisible();
      // «enheter», never the word for beer.
      const text = (await main.innerText()).toLowerCase();
      expect(text).toContain("enheter");
      expect(text).not.toMatch(/(?<!\p{L})øl(?!\p{L})/u);
      // One primary button, back to Hjem until the Startoppgave (Story 6.3).
      await expect(main.getByRole("link", { name: copy.done })).toHaveCount(1);
      await expectAccessible(page, vp.phone);
      await main.getByRole("link", { name: copy.done }).click();
      await expect(page).toHaveURL(/\/hjem$/);
    });
  });
}

test("Hjem's primary button «Les reglene» opens the briefing first", async ({ page }) => {
  await loginByApi(page, "student");
  await withGame(page, game(true));
  await page.goto("/hjem");
  await page.getByRole("main").getByRole("link", { name: home.readRules }).click();
  await expect(page).toHaveURL(new RegExp(`/spill/${GAME_ID}/regler$`));
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
});

test("with two games to brief, Hjem keeps one primary button and a Lenke for the second", async ({ page }) => {
  await loginByApi(page, "student");
  const second = { ...game(true), id: "01a1f8ee-34f2-70af-8800-f79281ed7770", number: 4 };
  await withGame(page, game(true), second);
  await page.goto("/hjem");
  const links = page.getByRole("main").getByRole("link", { name: home.readRules });
  await expect(links).toHaveCount(2);
  // The primary button is the Knapper look (`bg-ink`); the Lenke is underlined text.
  await expect(links.nth(0)).toHaveClass(/(^|\s)bg-ink(\s|$)/);
  await expect(links.nth(0)).toHaveAttribute("href", `/spill/${GAME_ID}/regler`);
  await expect(links.nth(1)).not.toHaveClass(/(^|\s)bg-ink(\s|$)/);
  await expect(links.nth(1)).toHaveAttribute("href", `/spill/${second.id}/regler`);
});

test("after the Starting task Hjem keeps the briefing as a Lenke", async ({ page }) => {
  await loginByApi(page, "student");
  await withGame(page, game(false));
  await page.goto("/hjem");
  const main = page.getByRole("main");
  await expect(main.getByRole("link", { name: home.readRules })).toHaveCount(0);
  await main.getByRole("link", { name: home.rulesLink }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.title);
});

test("a Fabrikk with changed settings reads its own delays and no Veiledede uker", async ({ page }) => {
  await loginByApi(page, "student");
  await withGame(page, game(true, { ...RULES, order_delay: 3, production_delay: 1, guided_weeks: 0 }, "factory"));
  await page.goto(`/spill/${GAME_ID}/regler`);
  const main = page.getByRole("main");
  await expect(
    main.getByText("Ordren din går til produksjon tre uker etter at du la den inn. Produksjonen tar én uke."),
  ).toBeVisible();
  await expect(main.getByText(copy.guided.none)).toBeVisible();
});

test("a game that is not the Student's shows the permission-denied page", async ({ page }) => {
  await loginByApi(page, "student");
  await page.goto(`/spill/${GAME_ID}/regler`); // the real api: no game of the demo Student
  await expect(page.getByText(nb.access.denied)).toBeVisible();
  await expect(page.getByRole("heading", { name: copy.title })).toHaveCount(0);
});
