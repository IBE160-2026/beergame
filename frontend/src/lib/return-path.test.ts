import { describe, expect, it } from "vitest";

import { loginPath, safeReturnPath } from "./return-path";

describe("safeReturnPath", () => {
  it("keeps a path on this site with its query and hash", () => {
    expect(safeReturnPath("/admin")).toBe("/admin");
    expect(safeReturnPath("/laererhjem?fane=2#klasse")).toBe("/laererhjem?fane=2#klasse");
    expect(safeReturnPath("/")).toBe("/");
  });

  it.each([
    ["another site", "https://evil.example/admin"],
    ["a protocol-relative address", "//evil.example"],
    ["a backslash", "/\\evil.example"],
    ["a scheme", "javascript:alert(1)"],
    ["a relative path", "admin"],
    ["a control character", "/admin\n"],
    ["a tab inside the slashes", "/\t/evil.example"],
    ["«Logg inn» itself", "/logg-inn?neste=%2Fadmin"],
    ["«Logg inn» with a trailing slash", "/logg-inn/"],
    ["an API address", "/api/auth/me"],
    ["an empty value", ""],
    ["a list", ["/admin"]],
    ["nothing", undefined],
  ])("drops %s", (_, raw) => {
    expect(safeReturnPath(raw)).toBeNull();
  });

  it("normalises dot segments before it checks the page", () => {
    expect(safeReturnPath("/admin/../logg-inn")).toBeNull();
    expect(safeReturnPath("/a/../admin")).toBe("/admin");
  });
});

describe("loginPath", () => {
  it("carries the way back and, for an ended session, the reason", () => {
    expect(loginPath("/admin")).toBe("/logg-inn?neste=%2Fadmin");
    expect(loginPath("/admin", true)).toBe("/logg-inn?neste=%2Fadmin&utlopt=1");
    expect(loginPath(null)).toBe("/logg-inn");
    expect(loginPath("//evil.example", true)).toBe("/logg-inn?utlopt=1");
  });
});
