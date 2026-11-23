import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { expectAccessible, freshClass, freshLecturer, test } from "./support/classes";

/** «Tilpassede oppgaver» (Story 11.9, FR-53, UX-DR70), on the local stack: the Lenke in «Spørsmål og
 * vekter», each draft template filled for the sample Student and labelled «Demodata», the draft
 * notice, the Adapted total weight and each item's share, and a locked session's pinned version. The
 * api's rules (the version it reads, every number from the fixture's rows, who may read it, no Game
 * and no LLM) are pinned by `backend/tests/individual_test/test_preview.py`. */
const copy = nb.tests.adaptedPreview;
const CSRF = { "X-Requested-With": "olspillet" };

async function newSession(lecturer: Page): Promise<string> {
  const klass = await freshClass(lecturer);
  const created = await lecturer.request.post(`/api/classes/${klass.id}/class-sessions`, { headers: CSRF });
  expect(created.status()).toBe(201);
  return (await created.json()).id;
}

const preview = (page: Page) => page.locator("[data-adapted-preview]");
const items = (page: Page) => preview(page).locator("[data-adapted-item]");

test("an owner opens the preview from «Spørsmål og vekter» and reads each template filled with Demodata", async ({
  page,
  browser,
}) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  await lecturer.goto(`/klasseokter/${id}`);
  const link = lecturer.locator("[data-question-adapted]").getByRole("link", { name: nb.tests.questionSet.adaptedPreview });
  await expect(link).toBeVisible();
  await link.click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${id}/tilpassede-oppgaver$`));
  await expect(lecturer.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
  await expect(preview(lecturer).getByText(nb.tests.questionSet.draft)).toBeVisible();
  await expect(preview(lecturer).locator("[data-adapted-preview-total]")).toHaveText(copy.total(30));

  const api = await (await lecturer.request.get(`/api/class-sessions/${id}/adapted-preview`)).json();
  await expect(items(lecturer)).toHaveCount(api.items.length);
  for (const [i, item] of (api.items as { id: string; source: string; weight: number; text: string }[]).entries()) {
    const shown = items(lecturer).nth(i);
    await expect(shown).toHaveAttribute("data-adapted-item", item.id);
    await expect(shown.getByRole("heading", { name: copy.item(i + 1) })).toBeVisible();
    await expect(shown.getByText(`${copy.sources[item.source]} · ${copy.weightText(item.weight)}`)).toBeVisible();
    await expect(shown.locator("blockquote")).toHaveText(item.text);
    await expect(shown.locator("figcaption")).toHaveText(nb.terms.demoData);
  }
  // The crumb leads back to the Klasseøkt.
  await lecturer.getByRole("navigation", { name: nb.navigation.breadcrumb }).getByRole("link", { name: nb.sessions.crumb }).click();
  await expect(lecturer).toHaveURL(new RegExp(`/klasseokter/${id}$`));
});

test("a locked session's preview shows the pinned Adapted total", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  const block = await (await lecturer.request.get(`/api/class-sessions/${id}/question-set`)).json();
  const weights = Object.fromEntries(block.items.map((i: { id: string; weight: number }) => [i.id, i.weight]));
  weights["langsvar-forsinkelse"] += 10;
  const saved = await lecturer.request.put(`/api/class-sessions/${id}/question-set`, {
    data: { weights, excluded: [], adapted_weight: 20 },
    headers: CSRF,
  });
  expect(saved.status()).toBe(200);
  expect((await lecturer.request.post(`/api/dev/class-sessions/${id}/lock`, { headers: CSRF })).status()).toBe(200);
  await lecturer.goto(`/klasseokter/${id}/tilpassede-oppgaver`);
  await expect(preview(lecturer).locator("[data-adapted-preview-total]")).toHaveText(copy.total(20));
  await expect(items(lecturer).first().getByText(copy.weightText(10), { exact: false })).toBeVisible();
});

test("a template the sample has no fact for says so instead of a text", async ({ page, browser }) => {
  const lecturer = await freshLecturer(page, browser);
  const id = await newSession(lecturer);
  // The server's answer for a template whose fact the sample game lacks (`text: null`).
  await lecturer.route(`**/api/class-sessions/${id}/adapted-preview`, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.items[1] = { ...body.items[1], text: null };
    await route.fulfill({ response, json: body });
  });
  try {
    await lecturer.goto(`/klasseokter/${id}/tilpassede-oppgaver`);
    await expect(items(lecturer).nth(1).getByText(copy.noFact)).toBeVisible();
    await expect(items(lecturer).nth(1).locator("blockquote")).toHaveCount(0);
    await expect(items(lecturer).first().locator("figcaption")).toHaveText(nb.terms.demoData);
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
  test.describe(`Tilpassede oppgaver, ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("the preview passes axe", async ({ page, browser }) => {
      const lecturer = await freshLecturer(page, browser);
      const id = await newSession(lecturer);
      await lecturer.goto(`/klasseokter/${id}/tilpassede-oppgaver`);
      await expect(items(lecturer).first().locator("figcaption")).toHaveText(nb.terms.demoData);
      await expectAccessible(lecturer, vp.phone);
    });
  });
}
