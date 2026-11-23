import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";
import { staffRecord } from "./support/record";

/** The Indicative letter (Story 12.6, FR-56, NFR-6, UX-DR12, UX-DR66) at 320, 360 and 1440 px with
 * axe and 44 px targets on phone:
 *
 * - on the stack, the Klasseøkt's «Veiledende bokstav»: the three Valgknapper with their scope in
 *   help text, saved with «Lagre Klasseøkt» and read back; the bounds of A to E, refused in place
 *   when they do not fall; stand-ins for the Institution's ban (only «Ikke tilgjengelig») and the
 *   read-only bounds;
 * - the Student's «Veiledende bokstav» Bryter on a ready «KI-vurdering» (stand-ins with the api's
 *   shapes): off, then on with the letter and its label beside the total, and the letter shown to
 *   everyone with no Bryter; the staff's Studentside shows a letter shown to everyone;
 * - on the stack, the Admin's Bryter on a fresh Institution in «Alle Institusjoner».
 *
 * Access, storage, the pin and who gets a letter are `backend/tests/assessment/test_letter.py`. */
const copy = nb.assessment.letterBlock;
const letterCopy = nb.assessment.letter;
const CSRF = { "X-Requested-With": "olspillet" };
const SESSION = "01a1f8ee-33b9-75e6-9502-79db27b37c0e";
const STUDENT_ID = "01a1f8ee-33b9-75e6-9502-79db27b37c99";

const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

const LONG = {
  id: "langsvar-forsinkelse",
  number: 1,
  type: "long",
  title: "Utkast: Forklar hvorfor ordrene svinger mer oppover i kjeden.",
  wording: null,
  weight: 100,
  points: 75,
  computed: null,
  ai: { assessed: true, step: 3, top: 4, label: "Utkast: godt", feedback: null, feedback_dropped: false, flagged: false },
};
const READY = { state: "ready", items: [LONG], unassessed: [], total: 75, total_max: 100, checked: false };
const CHOICE_OFF = { ...READY, letter: { setting: "student_choice", chosen: false, value: null } };
const CHOICE_ON = { ...READY, letter: { setting: "student_choice", chosen: true, value: "C" } };
const SHOWN = { ...READY, letter: { setting: "all", chosen: false, value: "C" } };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id;
}

const block = (page: Page) => page.locator("[data-letter-block]");
const save = (page: Page) => page.getByRole("button", { name: nb.sessions.save });

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

for (const vp of VIEWPORTS) {
  test.describe(`Klasseøkt, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("three settings with their scope, saved with «Lagre Klasseøkt»; the bounds; axe passes", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      const letter = block(lecturer);
      await expect(letter.getByRole("heading", { name: copy.title, exact: true })).toBeVisible();
      const group = letter.getByRole("group", { name: copy.legend });
      // The default, and its scope in help text tied to the group.
      await expect(group.getByRole("radio", { name: copy.options.student_choice })).toBeChecked();
      await expect(group).toHaveAccessibleDescription(copy.scope.student_choice);
      for (const value of ["all", "student_choice", "unavailable"] as const) {
        const radio = group.getByRole("radio", { name: copy.options[value] });
        await expect(radio).toBeVisible();
        if (vp.phone) {
          const box = await radio.boundingBox();
          expect(box && box.height >= 44 && box.width >= 44).toBe(true);
        }
      }
      await expect(letter.getByLabel(copy.bound("A"))).toHaveValue("90");
      await expect(letter.getByText(copy.rest)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);

      // Bounds that do not fall are refused in place; nothing is sent.
      await letter.getByLabel(copy.bound("B")).fill("95");
      await letter.getByLabel(copy.bound("B")).blur();
      await expect(letter.getByRole("alert")).toHaveText(copy.errors.out_of_order);
      await expectAccessible(lecturer, vp.phone);
      await letter.getByLabel(copy.bound("B")).fill("85");

      await group.getByText(copy.options.all, { exact: true }).click();
      await expect(group).toHaveAccessibleDescription(copy.scope.all);
      await save(lecturer).click();
      await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
      const stored = (await (await lecturer.request.get(`/api/class-sessions/${id}`)).json()).ai_assessment.letter;
      expect(stored.setting).toBe("all");
      expect(stored.thresholds).toEqual({ A: 90, B: 85, C: 60, D: 50, E: 40 });
      await lecturer.reload();
      await expect(block(lecturer).getByRole("radio", { name: copy.options.all })).toBeChecked();
      await expect(block(lecturer).getByLabel(copy.bound("B"))).toHaveValue("85");

      await block(lecturer).getByText(copy.options.unavailable, { exact: true }).click();
      await save(lecturer).click();
      await expect(lecturer.getByRole("status").filter({ hasText: nb.sessions.saved })).toBeVisible();
      await expect(block(lecturer).getByRole("radio", { name: copy.options.unavailable })).toBeChecked();
      await expectAccessible(lecturer, vp.phone);
    });

    test("the Institution's ban: only «Ikke tilgjengelig», with the reason; read-only bounds as text; axe passes", async ({
      page,
      browser,
    }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      // The api's answer where the Institution forbids the letter and a Student opened the test.
      await lecturer.route(`**/api/class-sessions/${id}`, async (route) => {
        if (route.request().method() !== "GET") return route.continue();
        const response = await route.fetch();
        const body = await response.json();
        const letter = { ...body.ai_assessment.letter, setting: "unavailable", stored: "all", forced: true, thresholds_open: false };
        await route.fulfill({ response, json: { ...body, ai_assessment: { ...body.ai_assessment, letter } } });
      });
      await lecturer.goto(`/klasseokter/${id}`);
      const letter = block(lecturer);
      await expect(letter.locator("[data-letter-forced]")).toHaveText(copy.forced);
      const group = letter.getByRole("group", { name: copy.legend });
      await expect(group.getByRole("radio", { name: copy.options.unavailable })).toBeChecked();
      await expect(group.getByRole("radio", { name: copy.options.all })).toHaveAttribute("aria-disabled", "true");
      await expect(group.getByRole("radio", { name: copy.options.student_choice })).toHaveAttribute("aria-disabled", "true");
      // A press on a forbidden option changes nothing (`force`: Playwright waits forever for an
      // `aria-disabled` control to become enabled).
      await group.getByText(copy.options.all, { exact: true }).click({ force: true });
      await expect(group.getByRole("radio", { name: copy.options.unavailable })).toBeChecked();
      await expect(letter.locator("[data-letter-bounds-text]")).toHaveText(
        "A fra 90 %, B fra 80 %, C fra 60 %, D fra 50 %, E fra 40 %. F: under grensen for E.",
      );
      await expect(letter.getByText(copy.thresholdsLocked)).toBeVisible();
      await expect(letter.getByRole("textbox")).toHaveCount(0);
      await expectAccessible(lecturer, vp.phone);
      await lecturer.unrouteAll({ behavior: "ignoreErrors" });
    });
  });

  test.describe(`Student, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("«Veiledende bokstav» turns the letter on beside the total and off again; axe passes", async ({ page }) => {
      await loginByApi(page, "student");
      let view: unknown = CHOICE_OFF;
      const sent: unknown[] = [];
      await page.route(`**/api/me/class-sessions/${SESSION}/test/assessment`, (route) =>
        route.fulfill({ status: 200, json: view }),
      );
      await page.route(`**/api/me/class-sessions/${SESSION}/test/assessment/letter`, (route) => {
        const body = route.request().postDataJSON() as { on: boolean };
        sent.push(body);
        view = body.on ? CHOICE_ON : CHOICE_OFF;
        return route.fulfill({ status: 200, json: view });
      });
      await page.goto(`/ki-vurdering/${SESSION}`);
      const total = page.locator("[data-total]");
      const toggle = total.getByRole("switch");
      await expect(toggle).toHaveAccessibleName(`${letterCopy.control} ${letterCopy.off}`);
      await expect(toggle).toHaveAttribute("aria-checked", "false");
      await expect(toggle).toHaveAccessibleDescription(letterCopy.help);
      await expect(total.locator("[data-letter]")).toHaveCount(0);
      if (vp.phone) {
        const box = await toggle.boundingBox();
        expect(box && box.height >= 44 && box.width >= 44).toBe(true);
      }
      await expectAccessible(page, vp.phone);

      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-checked", "true");
      await expect(total.locator("[data-letter]")).toContainText(letterCopy.value("C"));
      await expect(total.locator("[data-letter]")).toContainText(letterCopy.label);
      // Beside the total: under the sum line, inside its block.
      const sum = await total.getByText("Vektet sum: 75 av 100 poeng").boundingBox();
      const shown = await total.locator("[data-letter]").boundingBox();
      expect(shown!.y).toBeGreaterThan(sum!.y);
      await expectAccessible(page, vp.phone);

      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-checked", "false");
      await expect(total.locator("[data-letter]")).toHaveCount(0);
      expect(sent).toEqual([{ on: true }, { on: false }]);
    });

    test("shown to everyone: the letter with its label and no Bryter; the staff read the same; axe passes", async ({ page }) => {
      await loginByApi(page, "student");
      await page.route(`**/api/me/class-sessions/${SESSION}/test/assessment`, (route) =>
        route.fulfill({ status: 200, json: SHOWN }),
      );
      await page.goto(`/ki-vurdering/${SESSION}`);
      const total = page.locator("[data-total]");
      await expect(total.locator("[data-letter]")).toContainText(letterCopy.value("C"));
      await expect(total.locator("[data-letter]")).toContainText(letterCopy.label);
      await expect(total.getByRole("switch")).toHaveCount(0);
      await expectAccessible(page, vp.phone);
      await page.unrouteAll({ behavior: "ignoreErrors" });
    });
  });
}

test("staff: the Studentside shows a letter shown to everyone, with the same label", async ({ page }) => {
  await loginByApi(page, "assistant");
  await page.route(`**/api/class-sessions/${SESSION}/students/${STUDENT_ID}`, (route) =>
    route.fulfill({
      status: 200,
      json: {
        class_session_id: SESSION,
        class_id: "01a1f8ee-33b9-75e6-9502-79db27b37c98",
        class_name: "Logistikk 1",
        session_number: 1,
        user_id: STUDENT_ID,
        name: "Sara Student",
        class_share: 80,
        adjustment: null,
        deadlines: null,
        can_manage: false,
      },
    }),
  );
  await page.route(`**/api/class-sessions/${SESSION}/students/${STUDENT_ID}/record`, (route) =>
    route.fulfill({
      status: 200,
      json: staffRecord(
        { session: SESSION, classId: "01a1f8ee-33b9-75e6-9502-79db27b37c98", student: STUDENT_ID },
        { ...READY, letter: "C" },
      ),
    }),
  );
  await page.goto(`/klasseokter/${SESSION}/studenter/${STUDENT_ID}`);
  const total = page.locator("[data-staff-assessment] [data-total]");
  await expect(total.locator("[data-letter]")).toContainText(letterCopy.value("C"));
  await expect(total.locator("[data-letter]")).toContainText(letterCopy.label);
  await expect(total.getByRole("switch")).toHaveCount(0);
  await expectAccessible(page, false);
});

test("the Admin forbids the letter for a fresh Institution with its Bryter, and takes it back", async ({ page }) => {
  await loginByApi(page, "admin");
  const name = `Bokstavsperre ${Date.now()}`;
  const created = await page.request.post("/api/admin/institutions", { data: { name }, headers: CSRF });
  expect(created.status()).toBe(201);
  const id = (await created.json()).id;
  await page.goto("/admin/institusjoner");
  const toggle = page.locator(`#no-letter-switch-${id}`);
  const admin = nb.admin.institutions.noLetter;
  await expect(toggle).toHaveAccessibleName(`${admin.name(name)} ${admin.off}`);
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await toggle.click();
  await expect(page.getByRole("status").filter({ hasText: admin.saved(name, true) })).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(toggle).toHaveAccessibleName(`${admin.name(name)} ${admin.on}`);
  const listed = await (await page.request.get("/api/admin/institutions?limit=5")).json();
  expect(listed.items.find((each: { id: string }) => each.id === id).no_letter).toBe(true);
  await expectAccessible(page, false);
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-checked", "false");
});
