import { expect, type Locator, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** «Sensorveiledning» on the Klasseøkt (Story 11.2, FR-81, UX-DR49), on the local stack: the draft
 * guide with the five-step scale, one Tekstfelt per question with its label above it, «Standard»
 * or «Endret», the read-only criteria and «Ikke kontrollert med en Kontrolltest.»; an edit saved
 * and read back as «Endret»; and the read-only block after the Test-deadline lock (the local-only
 * `POST /api/dev/class-sessions/{id}/lock-test`). The api's rules (a new version per save, 409
 * `scoring_guide_locked`, the Assistant's 403, the pin, the copy, the load's 5-to-8 rule) are
 * pinned by `backend/tests/scoring_guide/test_scoring_guide.py`. */
const copy = nb.tests.scoringGuide;
const CSRF = { "X-Requested-With": "olspillet" };
const FIRST = "guide-langsvar-forsinkelse";
const SECOND = "guide-langsvar-informasjon";

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id;
}

async function lockTest(lecturer: Page, id: string) {
  const locked = await lecturer.request.post(`/api/dev/class-sessions/${id}/lock-test`, { headers: CSRF });
  expect(locked.status()).toBe(200);
}

const block = (page: Page) => page.locator("[data-scoring-guide]");
const row = (page: Page, id: string) => block(page).locator(`[data-guide="${id}"]`);
const field = (r: Locator) => r.getByRole("textbox");
const mark = (r: Locator) => r.locator("[data-guide-mark]");

test("an owner reads the draft guide, edits one text and reads it back as «Endret»", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByRole("heading", { name: copy.heading, level: 2 })).toBeVisible();
  await expect(block(lecturer).getByText(copy.draft)).toBeVisible();
  await expect(block(lecturer).getByText(copy.unchecked)).toBeVisible();
  await expect(block(lecturer).locator("[data-scoring-scale] li")).toHaveCount(5);
  const first = row(lecturer, FIRST);
  await expect(mark(first)).toHaveText(copy.standard);
  // The label sits above its Tekstfelt and names the question with it.
  const title = (await first.getByRole("heading", { level: 3 }).textContent()) ?? "";
  await expect(field(first)).toHaveAccessibleName(`${title} ${copy.guideLabel}`);
  const labelBox = await first.locator("label").boundingBox();
  const fieldBox = await field(first).boundingBox();
  expect(labelBox && fieldBox && labelBox.y + labelBox.height <= fieldBox.y + 1).toBe(true);
  // The criteria are text in a table, never fields.
  const criteria = first.locator("[data-guide-criteria]");
  await expect(criteria.getByRole("columnheader", { name: copy.code })).toBeVisible();
  await expect(criteria.getByRole("row")).toHaveCount(6);
  await expect(criteria.getByRole("textbox")).toHaveCount(0);

  const save = block(lecturer).getByRole("button", { name: copy.save });
  await expect(save).toHaveAttribute("aria-disabled", "true");
  // Emptied, the field says why and nothing can be saved.
  await field(first).fill("");
  await expect(first.getByText(copy.emptyGuide)).toBeVisible();
  await expect(save).toHaveAttribute("aria-disabled", "true");
  await field(first).fill("Se etter hvordan forsinkelsen gir for store ordrer.");
  await expect(mark(first)).toHaveText(copy.changed);
  await expect(save).not.toHaveAttribute("aria-disabled", "true");
  await save.click();
  await expect(block(lecturer).getByRole("status").filter({ hasText: copy.saved })).toBeVisible();
  const stored = await (await lecturer.request.get(`/api/class-sessions/${id}/scoring-guide`)).json();
  expect(stored.edited).toBe(true);
  expect(stored.questions.find((q: { id: string }) => q.id === FIRST).changed).toBe(true);
  await lecturer.reload();
  await expect(field(row(lecturer, FIRST))).toHaveValue("Se etter hvordan forsinkelsen gir for store ordrer.");
  await expect(mark(row(lecturer, FIRST))).toHaveText(copy.changed);
  await expect(mark(row(lecturer, SECOND))).toHaveText(copy.standard);
  await expect(block(lecturer).getByText(copy.unchecked)).toBeVisible();
});

test("after the Test-deadline lock the block stands as text and the api refuses an edit", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lockTest(lecturer, id);
  await lecturer.goto(`/klasseokter/${id}`);
  await expect(block(lecturer).getByText(copy.closed)).toBeVisible();
  await expect(block(lecturer).getByRole("textbox")).toHaveCount(0);
  await expect(block(lecturer).getByRole("button")).toHaveCount(0);
  await expect(row(lecturer, FIRST).getByText(copy.guideLabel)).toBeVisible();
  const refused = await lecturer.request.put(`/api/class-sessions/${id}/scoring-guide`, {
    data: { guides: { [FIRST]: "For sent." } },
    headers: CSRF,
  });
  expect(refused.status()).toBe(409);
  expect((await refused.json()).error.code).toBe("scoring_guide_locked");
});

test("an Assistant reads the block as text", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer to an Assistant lecturer (`scoring_guide.change` is the owners' only).
  await lecturer.route(`**/api/class-sessions/${id}/scoring-guide`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), can_change: false } });
  });
  try {
    await lecturer.goto(`/klasseokter/${id}`);
    await expect(block(lecturer).getByText(copy.assistant)).toBeVisible();
    await expect(block(lecturer).getByRole("textbox")).toHaveCount(0);
    await expect(mark(row(lecturer, FIRST))).toHaveText(copy.standard);
  } finally {
    await lecturer.unrouteAll({ behavior: "ignoreErrors" });
  }
});

const SIZES = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
];

for (const vp of SIZES) {
  test.describe(`Sensorveiledning, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("editable, changed and locked pass axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}`);
      const first = row(lecturer, FIRST);
      await expect(mark(first)).toHaveText(copy.standard);
      if (vp.phone) {
        // One column: the Tekstfelt is as wide as its question's row.
        const rowBox = await first.boundingBox();
        const fieldBox = await field(first).boundingBox();
        expect(rowBox && fieldBox && fieldBox.width > rowBox.width - 2).toBe(true);
      }
      await field(first).fill("Egen veiledning.");
      await expect(mark(first)).toHaveText(copy.changed);
      await expectAccessible(lecturer, vp.phone);

      const locked = await newSession(lecturer);
      await lockTest(lecturer, locked);
      await lecturer.goto(`/klasseokter/${locked}`);
      await expect(block(lecturer).getByText(copy.closed)).toBeVisible();
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
