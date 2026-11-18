import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { nb } from "../src/copy/nb";
import tokens from "../src/theme/tokens.json";

const copy = nb.auth.login;

/** "#B5423A" -> "rgb(181, 66, 58)", as getComputedStyle reports it. */
function rgb(token: keyof typeof tokens.colors) {
  const n = Number.parseInt(tokens.colors[token].slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
}
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

/** Widths from the story. 400 % zoom on a 1280 × 1024 screen is a 320 × 256 CSS-pixel viewport. */
const VIEWPORTS = [
  { name: "320 px", width: 320, height: 640, phone: true },
  { name: "360 px", width: 360, height: 740, phone: true },
  { name: "1440 px", width: 1440, height: 900, phone: false },
  { name: "400 % zoom", width: 320, height: 256, phone: true },
];

async function axeViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(WCAG_21_AA).analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

async function hasHorizontalScroll(page: Page) {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
}

/** Records every request to the API, so a test can show that nothing is sent. */
function apiRequests(page: Page) {
  const sent: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api")) sent.push(request.url());
  });
  return sent;
}

for (const vp of VIEWPORTS) {
  test.describe(vp.name, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("passes axe, reflows, and keeps text and tap targets large enough", async ({ page }) => {
      await page.goto("/logg-inn");
      await expect(page.getByRole("heading", { level: 1, name: copy.title })).toBeVisible();

      expect(await axeViolations(page)).toEqual([]);
      expect(await hasHorizontalScroll(page)).toBe(false);

      // Text: never under 13 px on a phone, no all caps, no letter-spacing.
      const text = await page.evaluate(() =>
        [...document.body.querySelectorAll<HTMLElement>("*")]
          .filter((el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent!.trim() !== ""))
          .map((el) => {
            const s = getComputedStyle(el);
            return { size: parseFloat(s.fontSize), transform: s.textTransform, spacing: s.letterSpacing };
          }),
      );
      expect(text.length).toBeGreaterThan(0);

      // No shadows and no gradients anywhere (UX-DR6).
      const decorated = await page.evaluate(() =>
        [...document.querySelectorAll<HTMLElement>("*")]
          .map((el) => getComputedStyle(el))
          .filter((s) => s.boxShadow !== "none" || s.backgroundImage !== "none" || s.textShadow !== "none").length,
      );
      expect(decorated).toBe(0);
      for (const t of text) {
        expect(t.size).toBeGreaterThanOrEqual(13);
        expect(t.transform).toBe("none");
        expect(t.spacing).toBe("normal");
      }

      // Tap targets of at least 44 px on the phone.
      if (vp.phone) {
        const boxes = await page.evaluate(() =>
          [...document.querySelectorAll<HTMLElement>("a, button, input")].map((el) => {
            const r = el.getBoundingClientRect();
            return { name: el.id || el.textContent, width: r.width, height: r.height };
          }),
        );
        const names = boxes.map((b) => b.name?.trim());
        for (const name of ["email", "password", copy.submit, copy.forgotPassword]) {
          expect(names).toContain(name);
        }
        for (const b of boxes) {
          expect(b.height, `${b.name} height`).toBeGreaterThanOrEqual(44);
          expect(b.width, `${b.name} width`).toBeGreaterThanOrEqual(44);
        }
      }

      // The invalid state passes axe and reflows too.
      await page.getByRole("button", { name: copy.submit }).click();
      await expect(page.getByText(copy.errors.emailEmpty)).toBeVisible();
      expect(await axeViolations(page)).toEqual([]);
      expect(await hasHorizontalScroll(page)).toBe(false);
    });
  });
}

test("uses the theme, the self-hosted font and paper as the only background", async ({ page }) => {
  const fontHosts: string[] = [];
  page.on("request", (request) => {
    const host = new URL(request.url()).hostname;
    if (/fonts\.(googleapis|gstatic)\.com$/.test(host)) fontHosts.push(host);
  });
  await page.goto("/logg-inn");
  await page.evaluate(() => document.fonts.ready);

  const style = await page.evaluate((names) => {
    const root = getComputedStyle(document.documentElement);
    const body = getComputedStyle(document.body);
    const h1 = getComputedStyle(document.querySelector("h1")!);
    return {
      vars: Object.fromEntries(names.map((n) => [n, root.getPropertyValue(`--color-${n}`).trim()])),
      background: body.backgroundColor,
      htmlBackground: root.backgroundColor,
      numeric: body.fontVariantNumeric,
      family: h1.fontFamily,
      loaded: [400, 600, 700].map((w) =>
        [...document.fonts].some(
          (face) => face.family.includes("Source Sans 3") && face.weight === String(w) && face.status === "loaded",
        ),
      ),
      colorScheme: root.colorScheme,
    };
  }, Object.keys(tokens.colors));

  // Every colour token reaches the page as a CSS variable (minified hex is expanded first).
  const expand = (hex: string) =>
    hex.length === 4 ? `#${[...hex.slice(1)].map((c) => c + c).join("")}` : hex;
  for (const [name, value] of Object.entries(tokens.colors)) {
    expect(expand(style.vars[name]).toUpperCase(), name).toBe(value.toUpperCase());
  }
  expect(style.background).toBe(rgb("paper"));
  expect(style.htmlBackground).toBe(rgb("paper"));
  expect(style.numeric).toBe("lining-nums tabular-nums");
  expect(style.family).toMatch(/^"Source Sans 3"/);
  expect(style.loaded).toEqual([true, true, true]);

  await page.emulateMedia({ colorScheme: "dark" });
  await page.reload();
  const dark = await page.evaluate(() => ({
    background: getComputedStyle(document.body).backgroundColor,
    text: getComputedStyle(document.querySelector("h1")!).color,
  }));
  expect(dark).toEqual({ background: rgb("paper"), text: rgb("ink") });
  expect(fontHosts).toEqual([]);
});

test("is operable by keyboard alone, with a visible focus ring", async ({ page }) => {
  const sent = apiRequests(page);
  await page.goto("/logg-inn");

  const order: string[] = [];
  for (let i = 0; i < 4; i++) {
    await page.keyboard.press("Tab");
    order.push(
      await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const s = getComputedStyle(el);
        if (s.outlineStyle !== "solid" || s.outlineWidth !== "2px" || s.outlineOffset !== "2px") return "no ring";
        return el.id || el.textContent!.trim();
      }),
    );
  }
  expect(order).toEqual(["email", "password", copy.submit, copy.forgotPassword]);
  await expect(page.getByLabel(copy.email)).not.toHaveAttribute("aria-invalid");
  await expect(page.getByLabel(copy.password)).not.toHaveAttribute("aria-invalid");

  // Back to «Logg inn» and press Enter: the empty form is checked and focus goes to E-post.
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Enter");
  const email = page.getByLabel(copy.email);
  await expect(email).toBeFocused();
  await expect(email).toHaveAttribute("aria-invalid", "true");
  await expect(email).toHaveAccessibleDescription(copy.errors.emailEmpty);
  await expect(page.getByLabel(copy.password)).toHaveAccessibleDescription(copy.errors.passwordEmpty);
  expect(sent).toEqual([]);
});

test("shows the reason beside a malformed e-mail, clears it when fixed, and sends nothing", async ({ page }) => {
  const sent = apiRequests(page);
  await page.goto("/logg-inn");
  const email = page.getByLabel(copy.email);
  const password = page.getByLabel(copy.password);
  const submit = page.getByRole("button", { name: copy.submit });

  for (const [value, reason] of [
    ["ola", copy.errors.emailNoAt],
    ["a@@b.no", copy.errors.emailTwoAt],
    ["ola@", copy.errors.emailNoDomain],
  ] as const) {
    await email.fill(value);
    await password.fill("hemmelig");
    await submit.click();
    await expect(email).toHaveAttribute("aria-invalid", "true");
    await expect(email).toHaveAccessibleDescription(reason);
    await expect(email).toBeFocused();
    await expect(password).not.toHaveAttribute("aria-invalid");
    const border = await email.evaluate((el) => getComputedStyle(el).borderTopColor);
    expect(border).toBe(rgb("restordre"));
  }

  // The password error clears when it is fixed and the field is left.
  await password.fill("");
  await submit.click();
  await expect(password).toHaveAccessibleDescription(copy.errors.passwordEmpty);
  await password.fill("hemmelig");
  await email.focus();
  await expect(password).not.toHaveAttribute("aria-invalid");
  await expect(page.getByText(copy.errors.passwordEmpty)).toHaveCount(0);

  // Fixed and left: the reason clears. Valid input: nothing is sent and the page stays.
  await email.fill("ola@uib.no");
  await password.focus();
  await expect(email).not.toHaveAttribute("aria-invalid");
  await submit.click();
  await expect(page.getByText(copy.errors.emailNoDomain)).toHaveCount(0);
  await expect(page).toHaveURL(/\/logg-inn$/);
  expect(sent).toEqual([]);
});
