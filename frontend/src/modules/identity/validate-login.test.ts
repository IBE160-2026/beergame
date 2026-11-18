import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { validateEmail, validateLogin } from "./validate-login";

describe("validateLogin", () => {
  it("marks both fields when both are empty", () => {
    expect(validateLogin({ email: "", password: "" })).toEqual({
      email: "emailEmpty",
      password: "passwordEmpty",
    });
  });

  it.each([
    ["   ", "emailEmpty"],
    ["ola", "emailNoAt"],
    ["a@@b.no", "emailTwoAt"],
    ["a@b@c.no", "emailTwoAt"],
    ["@uib.no", "emailNoLocal"],
    ["ola@", "emailNoDomain"],
    ["ola@uib", "emailNoDomain"],
    ["ola@uib.", "emailNoDomain"],
    ["ola@.no", "emailNoDomain"],
    ["ola nordmann@uib.no", "emailSpace"],
  ])("rejects %j as %s", (email, reason) => {
    expect(validateEmail(email)).toBe(reason);
  });

  it.each(["ola@uib.no", " Ola.Nordmann@student.uib.no ", "a@b.co"])("accepts %j", (email) => {
    expect(validateEmail(email)).toBeUndefined();
  });

  it("accepts valid input with no errors", () => {
    expect(validateLogin({ email: "ola@uib.no", password: "x" })).toEqual({});
  });

  it("has a Norwegian reason for every error key", () => {
    const keys = ["emailEmpty", "emailSpace", "emailNoAt", "emailTwoAt", "emailNoLocal", "emailNoDomain", "passwordEmpty"];
    for (const key of keys) {
      expect(nb.auth.login.errors[key as keyof typeof nb.auth.login.errors]).toBeTruthy();
    }
    expect(nb.auth.login.errors.emailNoAt).toBe("Mangler @");
    expect(nb.auth.login.errors.emailTwoAt).toBe("To @");
    expect(nb.auth.login.errors.emailNoDomain).toBe("Domene mangler");
  });
});
