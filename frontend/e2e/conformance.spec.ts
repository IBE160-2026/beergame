import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

import { type Browser, type BrowserContext, expect, type Page } from "@playwright/test";

import { demoSession, untilFontsLoaded } from "./support/auth";
import { axe } from "./support/axe";
import { type Session, test } from "./support/classes";
import { liveClassGame } from "./support/live-game";

/**
 * The conformance scan (Story 15.13, NFR-6): every surface of the product on this build, for every
 * Role, at 320, 360 and 1440 px, 400 % zoom, and 200 % text at 1280 and 320 px, with axe (WCAG 2.1 A/AA) and the
 * horizontal-scroll check. It records what it finds instead of failing on it: each viewport writes
 * one JSON file to `CONFORMANCE_OUT` (default `test-results/conformance`), and
 * `scripts/conformance-report.mjs` turns them into the dated report in `docs/accessibility/`.
 * `npm run conformance` runs both. Skipped unless `CONFORMANCE=1`: the specs of each screen already
 * fail on a violation, and this scan is the record, not a second gate.
 *
 * The data is fresh: one rule-based Class game of two new Students in a Class of the worker's fresh
 * Lecturer (never the demo Class). Student A plays it (Uke 1); Student B has the quiz passed through
 * the local dev route and a Replay started. The Debrief is scanned as the running game gives it.
 */
const ENABLED = process.env.CONFORMANCE === "1";
const OUT = process.env.CONFORMANCE_OUT ?? path.join("test-results", "conformance");
const CSRF = { "X-Requested-With": "olspillet" };

type ScanViewport = { id: string; label: string; width: number; height: number; text200?: boolean };

/** 400 % zoom on a 1280 × 1024 screen is a 320 × 256 CSS-pixel viewport (as `landing.spec.ts`). */
const SCAN_VIEWPORTS: ScanViewport[] = [
  { id: "320", label: "320 px", width: 320, height: 640 },
  { id: "360", label: "360 px", width: 360, height: 740 },
  { id: "1440", label: "1440 px", width: 1440, height: 900 },
  { id: "zoom400", label: "400 % zoom", width: 320, height: 256 },
  { id: "text200", label: "200 % text", width: 1280, height: 800, text200: true },
  { id: "text200-320", label: "320 px, 200 % text", width: 320, height: 640, text200: true },
];

type Actor = "public" | "studentA" | "studentB" | "lecturer" | "admin";
type Ids = { gameId: string; sessionId: string; replayId: string; classId: string };
type Surface = { surface: string; role: string; actor: Actor; path: (ids: Ids) => string };

const SURFACES: Surface[] = [
  { surface: "Landing", role: "Public", actor: "public", path: () => "/" },
  { surface: "Logg inn", role: "Public", actor: "public", path: () => "/logg-inn" },
  { surface: "Be om lærertilgang", role: "Public", actor: "public", path: () => "/laerertilgang" },
  { surface: "Glemt passord", role: "Public", actor: "public", path: () => "/glemt-passord" },
  { surface: "Tilgjengelighetserklæring", role: "Public", actor: "public", path: () => "/tilgjengelighet" },
  { surface: "Fant ikke siden", role: "Public", actor: "public", path: () => "/finnes-ikke" },
  { surface: "Hjem", role: "Student", actor: "studentA", path: () => "/hjem" },
  { surface: "Spill (play screen)", role: "Student", actor: "studentA", path: (ids) => `/spill/${ids.gameId}` },
  { surface: "Regler", role: "Student", actor: "studentA", path: (ids) => `/spill/${ids.gameId}/regler` },
  { surface: "Debrief (not yet open)", role: "Student", actor: "studentA", path: (ids) => `/debrief/${ids.sessionId}` },
  { surface: "Hjem with a Replay", role: "Student", actor: "studentB", path: () => "/hjem" },
  { surface: "Replay (play screen)", role: "Student", actor: "studentB", path: (ids) => `/spill/${ids.replayId}` },
  { surface: "Lærerhjem", role: "Lecturer", actor: "lecturer", path: () => "/laererhjem" },
  { surface: "Klasse", role: "Lecturer", actor: "lecturer", path: (ids) => `/klasser/${ids.classId}` },
  { surface: "Klasseøkt", role: "Lecturer", actor: "lecturer", path: (ids) => `/klasseokter/${ids.sessionId}` },
  { surface: "Oversikt", role: "Lecturer", actor: "lecturer", path: (ids) => `/klasseokter/${ids.sessionId}/oversikt` },
  {
    surface: "Spillinnsikt",
    role: "Lecturer",
    actor: "lecturer",
    path: (ids) => `/klasseokter/${ids.sessionId}/oversikt/spill/${ids.gameId}`,
  },
  { surface: "Admin", role: "Admin", actor: "admin", path: () => "/admin" },
  { surface: "Brukere", role: "Admin", actor: "admin", path: () => "/admin/brukere" },
  { surface: "Institusjoner", role: "Admin", actor: "admin", path: () => "/admin/institusjoner" },
  { surface: "Revisjonslogg", role: "Admin", actor: "admin", path: () => "/admin/revisjonslogg" },
  { surface: "Drift", role: "Admin", actor: "admin", path: () => "/admin/drift" },
  { surface: "KI-kostnad", role: "Admin", actor: "admin", path: () => "/admin/ki-kostnad" },
  { surface: "Pseudonymisert eksport", role: "Admin", actor: "admin", path: () => "/admin/evaluering" },
];

type ScanResult = {
  surface: string;
  role: string;
  /** The address with its ids named (`/spill/{gameId}`), for the report. */
  pattern: string;
  path: string;
  viewport: string;
  violations: { id: string; impact: string | null; help: string; targets: string[] }[];
  scrolls: boolean;
  error: string | null;
};

async function contextFor(
  browser: Browser,
  vp: ScanViewport,
  state: Session | undefined,
): Promise<BrowserContext> {
  const context = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: { width: vp.width, height: vp.height },
    storageState: state,
  });
  if (vp.text200) {
    await context.addInitScript(() => {
      document.addEventListener("DOMContentLoaded", () => {
        const style = document.createElement("style");
        style.textContent = "html { font-size: 200% !important; }";
        document.head.appendChild(style);
      });
    });
  }
  return context;
}

async function scan(page: Page, surface: Surface, ids: Ids, vp: ScanViewport): Promise<ScanResult> {
  const where = surface.path(ids);
  const result: ScanResult = {
    surface: surface.surface,
    role: surface.role,
    pattern: surface.path({ gameId: "{gameId}", sessionId: "{sessionId}", replayId: "{replayId}", classId: "{classId}" }),
    path: where,
    viewport: vp.id,
    violations: [],
    scrolls: false,
    error: null,
  };
  try {
    await page.goto(where);
    // Every page has one h1 once it has loaded (the Skjelett has none), and no Skjelett left.
    await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("[data-skeleton]")).toHaveCount(0, { timeout: 15_000 });
    // A page that sent the User elsewhere (an expired session to «Logg inn», a refusal to Hjem)
    // is not the surface: record it as not checked rather than pass the other page.
    const landed = new URL(page.url()).pathname;
    if (landed !== where) throw new Error(`opened ${landed} instead of ${where}`);
    await untilFontsLoaded(page);
    const found = await axe(page);
    result.violations = found.violations.map((v) => ({
      id: v.id,
      impact: v.impact ?? null,
      help: v.help,
      targets: v.nodes.map((n) => n.target.join(" ")),
    }));
    result.scrolls = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
  } catch (error) {
    result.error = String(error instanceof Error ? error.message : error).split("\n")[0]!;
  }
  return result;
}

test.describe("conformance scan", () => {
  test.skip(!ENABLED, "the conformance scan runs only with CONFORMANCE=1 (npm run conformance)");

  for (const vp of SCAN_VIEWPORTS) {
    test(`every surface at ${vp.label}`, async ({ browser, lecturerSession }) => {
      test.setTimeout(600_000);
      const game = await liveClassGame(browser, lecturerSession, 2, { aiMode: "rule_based" });
      const [a, b] = game.students;
      const passed = await b!.context.request.post(`/api/dev/class-sessions/${game.sessionId}/quiz-passed`, { headers: CSRF });
      expect(passed.status()).toBe(204);
      const started = await b!.context.request.post(`/api/me/class-sessions/${game.sessionId}/replay`, { headers: CSRF });
      expect(started.status()).toBe(201);
      const lecturerProbe = await contextFor(browser, vp, lecturerSession);
      const read = await lecturerProbe.request.get(`/api/class-sessions/${game.sessionId}`);
      expect(read.status()).toBe(200);
      const session = await read.json();
      expect(session.class_id).toBeTruthy();
      await lecturerProbe.close();
      const ids: Ids = {
        gameId: game.gameId,
        sessionId: game.sessionId,
        replayId: (await started.json()).game_id as string,
        classId: session.class_id as string,
      };
      const states: Record<Actor, Session | undefined> = {
        public: undefined,
        studentA: await a!.context.storageState(),
        studentB: await b!.context.storageState(),
        lecturer: lecturerSession,
        admin: { cookies: [demoSession("admin")], origins: [] },
      };

      const results: ScanResult[] = [];
      for (const actor of Object.keys(states) as Actor[]) {
        const context = await contextFor(browser, vp, states[actor]);
        const page = await context.newPage();
        for (const surface of SURFACES.filter((s) => s.actor === actor)) results.push(await scan(page, surface, ids, vp));
        await context.close();
      }
      mkdirSync(OUT, { recursive: true });
      writeFileSync(path.join(OUT, `${vp.id}.json`), JSON.stringify({ viewport: vp, results }, null, 2));
    });
  }
});
