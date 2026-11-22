import { expect, type Page } from "@playwright/test";

import { nb } from "../src/copy/nb";
import { loginByApi } from "./support/auth";
import { expectAccessible, lecturerPage, test } from "./support/classes";

/** The accessibility statement and the footer that links to it (Story 15.13, NFR-6). The statement
 * is public; the footer stands under every page but the print route and the shared screen. */
const copy = nb.accessibility;

function footerLink(page: Page) {
  return page.getByRole("contentinfo").getByRole("link", { name: copy.footerLink });
}

test("the Landing's footer leads to the statement, which a visitor reads without logging in", async ({ page }) => {
  await page.goto("/");
  const link = footerLink(page);
  await expect(link).toHaveAttribute("href", "/tilgjengelighet");
  await link.click();
  await expect(page).toHaveURL(/\/tilgjengelighet$/);
  await expect(page).toHaveTitle(`${copy.pageTitle} – ${nb.product.name}`);
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
  await expect(main.getByText(copy.updated)).toBeVisible();
  for (const title of [copy.standard.title, copy.deviations.title, copy.notYet.title, copy.tested.title, copy.contact.title, copy.complaint.title]) {
    await expect(main.getByRole("region", { name: title }).getByRole("heading", { level: 2, name: title })).toBeVisible();
  }
  // The known deviations, and the contact and complaint routes.
  const deviations = main.getByRole("region", { name: copy.deviations.title });
  if (copy.deviations.items.length > 0) await expect(deviations.getByRole("listitem")).toHaveText([...copy.deviations.items]);
  else await expect(deviations.getByText(copy.deviations.none)).toBeVisible();
  await expect(main.getByRole("region", { name: copy.notYet.title }).getByRole("listitem")).toHaveText([...copy.notYet.items]);
  const contact = main.getByRole("region", { name: copy.contact.title });
  await expect(contact.getByText(copy.contact.student)).toBeVisible();
  await expect(contact.getByRole("link", { name: copy.contact.email })).toHaveAttribute("href", `mailto:${copy.contact.email}`);
  await expect(main.getByRole("region", { name: copy.complaint.title }).getByRole("link", { name: copy.complaint.link })).toHaveAttribute(
    "href",
    copy.complaint.href,
  );
  // The footer is last in the tab order: after the page's own links.
  await footerLink(page).focus();
  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("link", { name: copy.complaint.link })).toBeFocused();
});

// The print route is not served through the proxy (only WeasyPrint reads it, inside the stack), so
// its exclusion is not reachable from here; the shared screen's is.
test("the footer stands under «Logg inn» and a logged-in page, and not under the shared screen", async ({ page }) => {
  await page.goto("/logg-inn");
  await expect(footerLink(page)).toBeVisible();
  await loginByApi(page, "student");
  await page.goto("/hjem");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(footerLink(page)).toBeVisible();
  // The footer is left out by the address alone, so the shared screen of an unknown Debrief has none either.
  await page.goto("/delt-skjerm/01a1aaaa-0000-7000-8000-0000000000d1");
  await expect(page).toHaveURL(/\/delt-skjerm\/01a1aaaa-0000-7000-8000-0000000000d1$/);
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("contentinfo")).toHaveCount(0);
});

for (const vp of [
  { name: "320 px", width: 320, height: 640, phone: true, text200: false },
  { name: "1440 px", width: 1440, height: 900, phone: false, text200: false },
  { name: "200 % text", width: 1280, height: 800, phone: false, text200: true },
  { name: "320 px with 200 % text", width: 320, height: 640, phone: true, text200: true },
]) {
  test(`the statement reflows and passes axe at ${vp.name}`, async ({ browser }) => {
    // No session: `lecturerPage` with an empty state gives a page at the size, with 200 % text.
    const page = await lecturerPage(browser, { cookies: [], origins: [] }, vp);
    await page.goto("/tilgjengelighet");
    await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();
    await expect(footerLink(page)).toBeVisible();
    await expectAccessible(page, vp.phone);
  });
}
