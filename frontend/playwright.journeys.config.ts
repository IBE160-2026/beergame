import { defineConfig, devices } from "@playwright/test";

// The Key User Journeys UJ-1 … UJ-9 (PRD §2.3) as one serial whole-course run against the local
// `docker compose` stack: `npm run e2e:journeys`. Not part of the default run (`playwright.config.ts`
// ignores `e2e/journeys`): it plays a whole Class game and takes many minutes.
export default defineConfig({
  testDir: "e2e/journeys",
  globalSetup: "./e2e/support/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 15 * 60_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8080",
    trace: { mode: "retain-on-failure", snapshots: true, screenshots: true, sources: true },
    screenshot: "only-on-failure",
    actionTimeout: 20_000,
  },
  projects: [
    {
      name: "journeys",
      use: {
        ...devices["Desktop Chrome"],
        locale: "nb-NO",
        timezoneId: "Europe/Oslo",
        launchOptions: { args: ["--lang=nb-NO"] },
      },
    },
  ],
});
