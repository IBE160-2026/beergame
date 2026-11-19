import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { actionErrorMessage } from "@/lib/api/mutation";

import { classErrors, classReasons, clean, firstInvalid, refusalFields, splitArchived } from "./classes";

const errors = nb.classes.errors;
const ok = { name: "class-of-1994", institution_id: "inst", course_code: "" };

describe("archived Classes (Story 4.10)", () => {
  it("lists the active Classes first and the archived ones apart, each in the api's order", () => {
    const items = [
      { id: "a", archived: true },
      { id: "b", archived: false },
      { id: "c", archived: true },
      { id: "d", archived: false },
    ];
    expect(splitArchived(items)).toEqual({
      active: [items[1], items[3]],
      archived: [items[0], items[2]],
    });
  });

  it("words `class_archived` the same for every action, unless the action words it itself", () => {
    const refused = new ApiRequestError(409, "class_archived");
    expect(actionErrorMessage(refused, {}, "Feil.")).toBe(nb.classes.archive.refused);
    expect(actionErrorMessage(refused, { class_archived: "Egen." }, "Feil.")).toBe("Egen.");
    expect(actionErrorMessage(new ApiRequestError(409, "other"), {}, "Feil.")).toBe("Feil.");
  });
});

describe("the Class rules", () => {
  it("trims and collapses whitespace as the api stores it", () => {
    expect(clean("  class-of   1994 ")).toBe("class-of 1994");
    // As Python's str.split: the separators U+001C–U+001F and U+0085 are whitespace.
    expect(clean("a\u001fb\u0085c")).toBe("a b c");
    expect(classReasons({ ...ok, name: "a\u001cb" })).toEqual({});
  });

  it("takes a name, an Institution and no course code", () => {
    expect(classReasons(ok)).toEqual({});
    expect(classReasons({ ...ok, name: "x".repeat(200), course_code: "C".repeat(50) })).toEqual({});
    expect(classReasons({ ...ok, name: "kari@usn.no" })).toEqual({});
  });

  it.each([
    [{ name: "  " }, { name: "name_empty" }],
    [{ name: "x".repeat(201) }, { name: "name_too_long" }],
    [{ name: "a\u0007b" }, { name: "name_invalid" }],
    [{ institution_id: "" }, { institution_id: "institution_missing" }],
    [{ course_code: "C".repeat(51) }, { course_code: "course_code_too_long" }],
    [{ course_code: "A\u0000" }, { course_code: "course_code_invalid" }],
  ])("refuses %j", (change, reasons) => {
    expect(classReasons({ ...ok, ...change })).toEqual(reasons);
  });

  it("words every refused field at once and names the first in form order", () => {
    const found = classErrors({ name: "", institution_id: "", course_code: "" });
    expect(found).toEqual({ name: errors.name_empty, institution_id: errors.institution_missing });
    expect(firstInvalid(found)).toBe("name");
    expect(firstInvalid({ course_code: "x", institution_id: "y" })).toBe("institution_id");
    expect(firstInvalid({})).toBeUndefined();
  });
});

describe("an api refusal", () => {
  it("goes beside the fields it names", () => {
    const refusal = new ApiRequestError(422, "invalid_request", {
      institution_id: "institution_unknown",
      name: "name_too_long",
    });
    expect(refusalFields(refusal)).toEqual({
      institution_id: errors.institution_unknown,
      name: errors.name_too_long,
    });
  });

  it("is a general failure for every other answer or an unknown reason", () => {
    expect(refusalFields(new ApiRequestError(500, "unknown_error"))).toEqual({});
    expect(refusalFields(new ApiRequestError(0, "network_error"))).toEqual({});
    expect(refusalFields(new ApiRequestError(422, "invalid_request", { name: "string_type" }))).toEqual({});
    expect(refusalFields(new Error("x"))).toEqual({});
  });
});

describe("the Lærerhjem labels", () => {
  it("names a Class with its course code when it has one", () => {
    expect(nb.classes.home.label("class-of-1994", "IBE160")).toBe("class-of-1994, IBE160");
    expect(nb.classes.home.label("class-of-1994", null)).toBe("class-of-1994");
    expect(nb.classes.page.facts("IBE160", "USN")).toBe("IBE160 · USN");
    expect(nb.classes.page.facts(null, "USN")).toBe("USN");
  });
});
