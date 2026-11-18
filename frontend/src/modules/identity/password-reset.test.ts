import { describe, expect, it } from "vitest";

import { tokenFromHash, validateNewPassword } from "./password-reset";

describe("validateNewPassword", () => {
  it.each([
    ["", "passwordEmpty"],
    ["1234567", "passwordShort"],
    ["🍺🍺🍺🍺🍺🍺🍺", "passwordShort"],
    ["12345678", undefined],
    ["et langt passord", undefined],
  ])("%j → %s", (value, expected) => {
    expect(validateNewPassword(value)).toBe(expected);
  });
});

describe("tokenFromHash", () => {
  it("reads the token from the fragment", () => {
    expect(tokenFromHash("#abc_DEF-123")).toBe("abc_DEF-123");
  });
  it.each(["", "#", "#abc def", "#a/b", `#${"a".repeat(129)}`])("is empty for %j", (hash) => {
    expect(tokenFromHash(hash)).toBe("");
  });
});
