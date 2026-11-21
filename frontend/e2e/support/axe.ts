import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";

/** WCAG 2.1 AA (NFR-6): every spec's axe check runs through here. Axe runs in the page itself
 * (`axe.run`, AxeBuilder's legacy mode): the app has no iframes, so it finds what the default mode
 * finds, without the blank page that mode opens and loads axe into for every check. Axe's half
 * megabyte is loaded into a page once, by this file (AxeBuilder would load it twice per check), and
 * AxeBuilder gets a no-op script. Together about two thirds of a check's time, over several hundred
 * checks in the suite. The axe-core is the one `@axe-core/playwright` brings. */
const WCAG_21_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
const SOURCE = readFileSync(createRequire(require.resolve("@axe-core/playwright")).resolve("axe-core/axe.min.js"), "utf8");

export async function axe(page: Page) {
  const loaded = await page.evaluate(() => typeof (window as { axe?: { run?: unknown } }).axe?.run === "function");
  if (!loaded) await page.evaluate(SOURCE);
  return new AxeBuilder({ page, axeSource: ";" }).withTags(WCAG_21_AA).setLegacyMode().analyze();
}
