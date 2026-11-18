import { type FullConfig, request } from "@playwright/test";

import { DEMO_PASSWORD, DEMO_USERS, type DemoRole, SESSIONS_ENV } from "./auth";

/**
 * Logs in each demo User once, one after the other, before any test runs, and hands the session
 * cookies to the workers (through the environment, which they inherit). The login rate limit
 * counts an attempt before it checks the password and a success clears the count, so more than
 * five demo Admin logins in flight at once, as parallel workers would send, are refused. With the
 * cookies shared, a test that needs a session takes one instead of logging in.
 */
export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL;
  const sessions: Partial<Record<DemoRole, unknown>> = {};
  for (const role of Object.keys(DEMO_USERS) as DemoRole[]) {
    const context = await request.newContext({ baseURL });
    const response = await context.post("/api/auth/login", {
      data: { email: DEMO_USERS[role].email, password: DEMO_PASSWORD },
      headers: { "X-Requested-With": "olspillet" },
    });
    if (response.status() !== 200) throw new Error(`login of the demo ${role} answered ${response.status()}`);
    const [cookie] = (await context.storageState()).cookies.filter((c) => c.name === "olspillet_session");
    sessions[role] = cookie;
    await context.dispose();
  }
  process.env[SESSIONS_ENV] = JSON.stringify(sessions);
}
