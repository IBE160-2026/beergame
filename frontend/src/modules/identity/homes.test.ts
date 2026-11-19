import { describe, expect, it } from "vitest";

import { canCreateClass, canView, HOME_LINK, HOME_PATH, type Home, homeOf } from "./homes";

const admin = { roles: ["admin"] };
const lecturer = { roles: ["lecturer"] };
const both = { roles: ["admin", "lecturer"] };
const none = { roles: [] };
const assistant = { roles: ["assistant"] };

describe("homeOf", () => {
  it("sends each User to their own home; Admin and Lecturer lands on the Lærerhjem", () => {
    expect(homeOf(admin)).toBe("adminArea");
    expect(homeOf(lecturer)).toBe("lecturerHome");
    expect(homeOf(both)).toBe("lecturerHome");
    expect(homeOf(none)).toBe("home");
  });

  it("sends an Assistent to the Lærerhjem, where they may not create a Class (Story 4.9)", () => {
    expect(homeOf(assistant)).toBe("lecturerHome");
    expect(homeOf({ roles: ["admin", "assistant"] })).toBe("lecturerHome");
    expect(canCreateClass(assistant)).toBe(false);
    expect(canCreateClass(lecturer)).toBe(true);
  });
});

describe("canView", () => {
  const table: [Home, Record<string, boolean>][] = [
    ["adminArea", { admin: true, lecturer: false, both: true, none: false, assistant: false }],
    ["lecturerHome", { admin: false, lecturer: true, both: true, none: false, assistant: true }],
    ["home", { admin: false, lecturer: false, both: false, none: true, assistant: false }],
  ];
  const users = { admin, lecturer, both, none, assistant };
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
