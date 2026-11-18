import { describe, expect, it } from "vitest";

import { canView, HOME_LINK, HOME_PATH, type Home, homeOf } from "./homes";

const admin = { roles: ["admin"] };
const lecturer = { roles: ["lecturer"] };
const both = { roles: ["admin", "lecturer"] };
const none = { roles: [] };

describe("homeOf", () => {
  it("sends each User to their own home; Admin and Lecturer lands on the Lærerhjem", () => {
    expect(homeOf(admin)).toBe("adminArea");
    expect(homeOf(lecturer)).toBe("lecturerHome");
    expect(homeOf(both)).toBe("lecturerHome");
    expect(homeOf(none)).toBe("home");
  });
});

describe("canView", () => {
  const table: [Home, Record<string, boolean>][] = [
    ["adminArea", { admin: true, lecturer: false, both: true, none: false }],
    ["lecturerHome", { admin: false, lecturer: true, both: true, none: false }],
    ["home", { admin: false, lecturer: false, both: false, none: true }],
  ];
  const users = { admin, lecturer, both, none };
  for (const [page, expected] of table) {
    it(`lets only the right Users open ${page}`, () => {
      for (const [name, user] of Object.entries(users)) {
        expect(canView(page, user), name).toBe(expected[name]);
      }
    });
  }

  it("always lets a User open their own home", () => {
    for (const user of Object.values(users)) expect(canView(homeOf(user), user)).toBe(true);
  });
});

it("has a path and a link text for every home", () => {
  expect(HOME_PATH).toEqual({ adminArea: "/admin", lecturerHome: "/laererhjem", home: "/hjem" });
  expect(Object.values(HOME_LINK)).toEqual(["Til Admin-område", "Til Lærerhjem", "Til Hjem"]);
});
