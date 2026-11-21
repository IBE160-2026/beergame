import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { formatNumber } from "../src/lib/number-format";
import { expectAccessible, test } from "./support/classes";
import { alignment, labelProblems, textReadable } from "./support/graph";
import { openPlay, orderField } from "./support/play";

/** «Kostnad så langt» and «Alle rader og kostnad» (Story 6.16, FR-23, FR-73, NFR-6, UX-DR13,
 * UX-DR21, UX-DR22) on the play screen with the stand-in Uke 11 (`support/play.ts`), and the
 * Landing's Demodata panel. The numbers' source is `src/modules/games/cost-panel.test.tsx`. */
const copy = nb.games.play;
const kr = (value: string) => formatNumber(value, { kroner: true });
const totalButton = (page: Page) => page.getByRole("button", { name: copy.totalCostButton(kr("82")) });
const allRowsTitle = (page: Page) => page.getByRole("heading", { level: 1, name: copy.allRows.title(11) });
const close = (page: Page) => page.getByRole("button", { name: copy.allRows.close });
const panel = (page: Page) => page.locator("[data-cost-panel]").filter({ visible: true });

async function text200(page: Page) {
  await page.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const style = document.createElement("style");
      style.textContent = "html { font-size: 200% !important; }";
      document.head.appendChild(style);
    });
  });
}

test.describe("phone", () => {
  test.use({ viewport: { width: 360, height: 740 } });

  test("the Totalkostnad button opens Alle rader; «Lukk» returns with the typed Order and focus", async ({ page }) => {
    await openPlay(page);
    await orderField(page).fill("24");
    const button = totalButton(page);
    expect((await button.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await button.click();

    await expect(allRowsTitle(page)).toBeFocused();
    await expect(page.locator("[data-all-rows]").getByText(copy.roleGame("Grossist", 17), { exact: true })).toBeVisible();
    await expect(close(page)).toBeVisible();
    // The play screen is gone from view, not overlaid: no Ordrefelt, no Topplinje.
    await expect(orderField(page)).toBeHidden();
    await expect(button).toBeHidden();
    const region = page.getByRole("region", { name: copy.table.region });
    const rows = await region.locator("tbody tr").evaluateAll((trs) =>
      trs.filter((tr) => getComputedStyle(tr).display !== "none").map((tr) => tr.querySelector("th")!.textContent),
    );
    expect(rows).toEqual([
      "Ordre inn",
      "Levering",
      "Sendt",
      "Lager",
      "Restordre",
      "Netto lager",
      "På vei",
      "Posisjon",
      "Din ordre",
      "Kost per uke",
      "Sum, kr",
    ]);
    // The typed 24 is previewed here too, and «Sum, kr» at nå is the Totalkostnad.
    await expect(region.locator("tr[data-row=order] td[data-join=from]")).toHaveText(/^24/);
    await expect(region.locator("tr[data-row=totalCost] td").filter({ visible: true }).nth(7)).toHaveText("82");
    await expect(page.locator("[data-column-lines] > div")).toHaveText([
      "Netto lager i kolonne 11−14 + 4 − 10 = −20",
      "Posisjon i kolonne 11−20 + 16 = −4",
    ]);
    const cost = panel(page);
    await expect(cost.getByRole("heading", { name: copy.costPanel.title })).toBeVisible();
    await expect(cost.locator("dl > div")).toHaveText([
      `Lagerkostnad${kr("40")}`,
      `Restordrekostnad${kr("42")}`,
      `Totalkostnad${kr("82")}`,
    ]);
    await expect(cost.locator("svg[data-chart=cost-area]")).toHaveAttribute("aria-hidden", "true");
    await expect(cost.getByRole("button", { name: copy.costPanel.showTable })).toHaveCount(0);
    await expect(cost.getByText(copy.allRows.sumRowNote)).toBeAttached();
    await expect(cost.getByText(`Denne uka: 20 restordre × 1,00 = ${kr("20")}`)).toBeVisible();
    // Graf over tabell over all the rows passes the alignment check of Story 6.7.
    const found = await alignment(page);
    expect(found.off).toEqual([]);
    expect(found.nowLine).toBeLessThanOrEqual(1);
    expect(await labelProblems(page)).toEqual([]);

    await close(page).click();
    await expect(orderField(page)).toHaveValue("24");
    await expect(button).toBeFocused();
  });

  test("«Alle rader og kostnad» and the Uke-overgang's «Kostnad så langt» open it, at the panel for the latter", async ({
    page,
  }) => {
    await openPlay(page);
    const link = page.getByRole("button", { name: copy.allRows.link, exact: true });
    await link.click();
    await expect(allRowsTitle(page)).toBeFocused();
    await page.keyboard.press("Escape"); // closes as «Lukk» does
    await expect(link).toBeFocused();

    const costLink = page.locator("[data-week-summary]").getByRole("button", { name: copy.summary.costLink });
    await costLink.click();
    const heading = panel(page).getByRole("heading", { name: copy.costPanel.title });
    await expect(heading).toBeFocused();
    await expect(heading).toBeInViewport();
    await close(page).click();
    await expect(costLink).toBeFocused();
  });
});

test.describe("laptop", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("«Kostnad så langt» is pinned under the Ordrefelt, and «Vis som tabell» opens its table in place", async ({ page }) => {
    await openPlay(page);
    const cost = panel(page);
    await expect(cost).toBeVisible();
    const field = (await page.locator("[data-order-field]").boundingBox())!;
    const box = (await cost.boundingBox())!;
    expect(box.y).toBeGreaterThan(field.y + field.height);
    expect(box.x).toBeGreaterThanOrEqual(field.x - 1);
    // Already pinned: neither phone way to it shows, and the Totalkostnad pair is plain text.
    await expect(page.getByRole("button", { name: copy.totalCostButton(kr("82")) })).toBeHidden();
    await expect(page.getByRole("button", { name: copy.allRows.link, exact: true })).toBeHidden();
    await expect(page.getByRole("button", { name: copy.summary.costLink })).toBeHidden();

    const toggle = cost.locator("[data-cost-toggle]");
    await expect(toggle).toHaveText(copy.costPanel.showTable);
    await toggle.click();
    await expect(toggle).toHaveText(copy.costPanel.showChart);
    await expect(cost.locator("svg[data-chart=cost-area]")).toHaveCount(0);
    const table = cost.getByRole("table");
    await expect(table.getByRole("columnheader")).toHaveText(["Uke", "Lager", "Restordre", "Sum, kr"]);
    await expect(table.locator("tbody tr")).toHaveCount(11);
    await expect(table.locator("tbody tr").last()).toHaveText("1140,0042,0082,00");
    await toggle.click();
    await expect(cost.locator("svg[data-chart=cost-area]")).toBeVisible();
  });
});

const WIDTHS = [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "360 px", width: 360, height: 740, phone: true, text200: false },
  { name: "360 px with 200 % text", width: 360, height: 740, phone: true, text200: true },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
];

for (const vp of WIDTHS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("Alle rader (phone) or the pinned panel reflows with no axe violation and no text under 13 px", async ({ page }) => {
      if (vp.text200) await text200(page);
      await openPlay(page);
      if (vp.phone) {
        await totalButton(page).click();
        await expect(allRowsTitle(page)).toBeFocused();
      }
      await expect(panel(page)).toBeVisible();
      await expectAccessible(page, vp.phone);
      await textReadable(page);
      expect(await labelProblems(page)).toEqual([]);
    });
  });
}

test.describe("Landing", () => {
  test("the Demodata Seat's «Kostnad så langt» stands right of the figure at 1440 px and after it on phone", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/");
    const cost = page.locator("[data-cost-panel]");
    await expect(cost.getByRole("heading", { name: copy.costPanel.title })).toBeVisible();
    await expect(cost.locator("dl > div")).toHaveText([`Lagerkostnad${kr("24")}`, `Restordrekostnad${kr("0")}`, `Totalkostnad${kr("24")}`]);
    await expect(cost.getByText(nb.landing.seat.demoData, { exact: true })).toBeVisible();
    await expect(cost.getByText(`Denne uka: 12 lager × 0,50 = ${kr("6")}`)).toBeVisible();
    const figure = (await page.locator("figure").boundingBox())!;
    let box = (await cost.boundingBox())!;
    expect(box.x).toBeGreaterThanOrEqual(figure.x + figure.width);
    expect(box.y).toBeLessThan(figure.y + figure.height);

    await page.setViewportSize({ width: 360, height: 740 });
    box = (await cost.boundingBox())!;
    const below = (await page.locator("figure").boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(below.y + below.height);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  });
});
