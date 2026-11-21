import { expect, type Page } from "@playwright/test";

import result from "../src/modules/games/fixtures/result-classic.json";
import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { BILL, STAFF_SUMMARY, SUMMARY } from "./support/bill";
import { expectAccessible, expectReflow, test } from "./support/classes";
import { MOMENTS } from "./support/moments";
import { QUESTIONS } from "./support/reflection";
import { REVEAL } from "./support/reveal";

/** The end of Debrief step 4 and the staff's summary page (Story 9.8, FR-44, FR-47, NFR-6,
 * UX-DR36, AD-10). From stand-in answers of the Debrief endpoints with every reflection question
 * answered: Kjedens regning as «Spillet er ferdig» drew it, with «(deg)», «Kjeden», the two
 * «Simulert, samme kunder» rows after it, the restordre and AI lines and Kjedens kostnad over tid;
 * «Fullfør Debriefen» and the finished line, focused; a finished Debrief read again with nothing to
 * send; and the staff page with the Explanation, moments and answers. At 320, 360 and 1440 px with
 * axe. The api's numbers, storage and refusals are `backend/tests/debrief/test_explanation.py`. */
const copy = nb.debrief.bill;
const chainCopy = nb.games.play.chain;
const SESSION = "01a1aaaa-0000-7000-8000-000000000098";
const DEBRIEF = "01a1aaaa-0000-7000-8000-0000000009d8";
const GAME = "01a1aaaa-0000-7000-8000-0000000009a7";
const OPENED = { id: DEBRIEF, class_session_id: SESSION, game_id: GAME, game_number: 17, role: "wholesaler", step: 1 };
const SENT = { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" };
const ANSWER = { text: "Svar.", length: 5, saved_at: "2026-11-21T12:10:00Z" };
const STEP = { debrief_id: DEBRIEF, reveal: null, chain: null, moments: null, bill: null };

/** The open Debrief at the end of step 4; `finished` answers a stored summary from the start. */
async function atTheBill(page: Page, { finished = false, refuse = null as string | null } = {}) {
  let summary: object | null = finished ? SUMMARY : null;
  const finishes: string[] = [];
  await page.route(`**/api/me/class-sessions/${SESSION}/debrief`, (route) => route.fulfill({ json: OPENED }));
  await page.route(`**/api/debriefs/${DEBRIEF}/net-inventory`, (route) =>
    route.fulfill({ json: { weeks: REVEAL.weeks.map((w) => ({ week: w.week, net_inventory: 12 - w.week })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/explanation`, (route) => route.fulfill({ json: { explanation: SENT } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/2`, (route) => route.fulfill({ json: { ...STEP, step: 2, reveal: REVEAL } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/3`, (route) => route.fulfill({ json: { ...STEP, step: 3 } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/reflection`, (route) =>
    route.fulfill({ json: { version: 1, questions: QUESTIONS.map((q) => ({ ...q, answer: ANSWER })) } }),
  );
  await page.route(`**/api/debriefs/${DEBRIEF}/steps/4`, (route) =>
    route.fulfill({ json: { ...STEP, step: 4, moments: MOMENTS, bill: BILL } }),
  );
  await page.route(`**/api/me/games/${GAME}/result`, (route) => route.fulfill({ json: result }));
  await page.route(`**/api/debriefs/${DEBRIEF}/summary`, (route) => route.fulfill({ json: { summary } }));
  await page.route(`**/api/debriefs/${DEBRIEF}/finish`, (route) => {
    finishes.push(route.request().method());
    if (refuse) return route.fulfill({ status: 409, json: { error: { code: refuse, message: "x" } } });
    summary = SUMMARY;
    return route.fulfill({ json: { summary } });
  });
  return { finishes, unroute: () => page.unrouteAll({ behavior: "ignoreErrors" }) };
}

function bill(page: Page) {
  return page.locator("[data-debrief-bill]");
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("Kjedens regning with the Simulert rows after Kjeden, then «Fullfør Debriefen»", async ({ page }) => {
      await loginByApi(page, "student");
      const stub = await atTheBill(page);
      await page.goto(`/debrief/${SESSION}`);
      const end = bill(page);
      const table = end.getByRole("table");
      await expect(end.getByRole("heading", { level: 2, name: chainCopy.bill })).toBeVisible();
      // Detaljist to Fabrikk, the own row marked, Kjeden, then «Simulert, samme kunder».
      const heads = table.getByRole("rowheader");
      await expect(heads).toHaveText([
        "Detaljist",
        "Grossist (deg)",
        "Distributør",
        "Fabrikk",
        chainCopy.chain,
        copy.simulated,
        copy.simulatedOwn,
        copy.simulatedAll,
      ]);
      await expect(table.locator("[data-chain-row]")).toContainText("2 266,00");
      await expect(table.locator("[data-simulated-row=own]")).toContainText("1 507,00");
      await expect(table.locator("[data-simulated-row=all]")).toContainText("1 341,00");
      // The split bar's numbers stand in its row.
      await expect(table.locator("[data-role=wholesaler]")).toContainText("154,50");
      await expect(end.locator("[data-simulated-note]")).toHaveText(copy.simulatedNote);
      await expect(end.locator("[data-backorder-share]")).toHaveText(copy.shareDouble(60));
      await expect(end.locator("[data-ai-share]")).toHaveText(copy.aiShare(12, "271,50 kr"));
      await expect(end.getByRole("button", { name: chainCopy.showTable })).toBeVisible();
      await expectAccessible(page, viewport.phone);
      await expectReflow(page, viewport.phone);

      const finish = end.getByRole("button", { name: copy.finish });
      await finish.focus();
      await page.keyboard.press("Enter");
      const done = end.locator("[data-debrief-finished]");
      await expect(done).toHaveText(/Debriefen er fullført .*14:05\. /);
      await expect(done).toBeFocused();
      await expect(finish).toHaveCount(0);
      expect(stub.finishes).toEqual(["POST"]);
      await stub.unroute();
    });
  });
}

test("a finished Debrief reads again with nothing to send", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atTheBill(page, { finished: true });
  await page.goto(`/debrief/${SESSION}`);
  await expect(bill(page).locator("[data-debrief-finished]")).toBeVisible();
  await expect(page.locator("[data-debrief-moments]")).toBeVisible();
  await expect(page.locator("[data-debrief-reveal]")).toBeVisible();
  // Every step stands; no field, no send, no finish.
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await expect(page.getByRole("button", { name: copy.finish })).toHaveCount(0);
  await expect(page.getByRole("button", { name: nb.debriefEntry.explanation.send })).toHaveCount(0);
  expect(stub.finishes).toEqual([]);
  await stub.unroute();
});

test("a failed read of the summary says so, and «Prøv igjen» brings the button", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atTheBill(page);
  let failing = true;
  await page.route(`**/api/debriefs/${DEBRIEF}/summary`, (route) =>
    failing
      ? route.fulfill({ status: 500, json: { error: { code: "internal", message: "x" } } })
      : route.fulfill({ json: { summary: null } }),
  );
  await page.goto(`/debrief/${SESSION}`);
  const failed = bill(page).locator("[data-debrief-finish=failed]");
  await expect(failed).toContainText(copy.summaryFailed);
  failing = false;
  await failed.getByRole("button", { name: nb.system.retry }).click();
  await expect(bill(page).getByRole("button", { name: copy.finish })).toBeVisible();
  await stub.unroute();
});

test("a refused finish says why beside the button", async ({ page }) => {
  await loginByApi(page, "student");
  const stub = await atTheBill(page, { refuse: "test_deadline_passed" });
  await page.goto(`/debrief/${SESSION}`);
  await bill(page).getByRole("button", { name: copy.finish }).click();
  await expect(bill(page)).toContainText(copy.deadlinePassed);
  await expect(bill(page).locator("[data-debrief-finished]")).toHaveCount(0);
  await stub.unroute();
});

const STAFF_PATH = `/klasseokter/${SESSION}/studenter/${STAFF_SUMMARY.student_id}/debrief`;
const staff = nb.debrief.staffSummary;

async function stubStaff(page: Page, status = 200) {
  await page.route(`**/api/class-sessions/${SESSION}/students/${STAFF_SUMMARY.student_id}/debrief-summary`, (route) =>
    status === 200
      ? route.fulfill({ json: STAFF_SUMMARY })
      : route.fulfill({ status, json: { error: { code: "forbidden", message: "x" } } }),
  );
  return () => page.unrouteAll({ behavior: "ignoreErrors" });
}

for (const viewport of [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
]) {
  test(`the staff read a Student's Explanation and Debrief summary at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await loginByApi(page, "lecturer");
    const unroute = await stubStaff(page);
    await page.goto(STAFF_PATH);
    await expect(page.getByRole("heading", { level: 1, name: staff.title })).toBeVisible();
    await expect(page.locator("[data-summary-explanation]")).toContainText(STAFF_SUMMARY.explanation.text);
    const finished = page.locator("[data-summary-finished]");
    await expect(finished).toContainText(/Fullført .*14:05\./);
    await expect(finished).toContainText(staff.late);
    await expect(page.locator("[data-summary-moment]")).toHaveCount(3);
    await expect(page.locator("[data-summary-moment]").first()).toContainText(MOMENTS.moments[0]!.reckoning.text);
    await expect(page.locator("[data-summary-answer=evidence]")).toContainText("Fabrikken svingte mest.");
    await expectAccessible(page, viewport.phone);
    await expectReflow(page, viewport.phone);
    await unroute();
  });
}

test("a caller the api refuses gets the permission-denied page", async ({ page }) => {
  await loginByApi(page, "lecturer");
  const unroute = await stubStaff(page, 403);
  await page.goto(STAFF_PATH);
  await expect(page.getByText(nb.access.denied)).toBeVisible();
  await expect(page.locator("[data-summary-explanation]")).toHaveCount(0);
  await unroute();
});
