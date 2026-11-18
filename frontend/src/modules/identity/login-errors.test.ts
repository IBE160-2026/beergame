import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { loginErrorMessage } from "./login-errors";

const copy = nb.auth.login;

describe("loginErrorMessage", () => {
  it.each([
    ["invalid_credentials", copy.invalidCredentials],
    ["account_deactivated", copy.deactivated],
    ["rate_limited", copy.rateLimited],
    ["invalid_request", copy.failed],
    ["network_error", copy.failed],
    ["unknown_error", copy.failed],
  ])("maps %s to its line in nb.ts", (code, line) => {
    expect(loginErrorMessage(code)).toBe(line);
  });

  it("never names a field or whether the account exists", () => {
    expect(copy.invalidCredentials).toBe("Feil e-post eller passord.");
  });
});
