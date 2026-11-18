import { defineConfig, devices } from "@playwright/test";

// Runs against the local `docker compose` stack through the proxy. Use 127.0.0.1, not localhost:
// a local WSL relay listens on ::1.
export default defineConfig({
  testDir: "e2e",
  // One login per demo User for the whole run, shared by the workers (see the file).
  globalSetup: "./e2e/support/global-setup.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8080",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
