import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";

import { myDataKey } from "./api";

import { fieldLabel, fieldValue, itemHeading } from "./my-data";

const copy = nb.myData;

describe("«Mine data» values (Story 15.1)", () => {
  it("labels codes from nb.ts and shows an unknown code as stored", () => {
    expect(fieldValue({ key: "decided_by", kind: "code", value: "student" })).toBe(copy.codes.decided_by!.student);
    expect(fieldValue({ key: "role", kind: "code", value: "factory" })).toBe("Fabrikk");
    expect(fieldValue({ key: "item_id", kind: "code", value: "q-7" })).toBe("q-7");
  });

  it("shows yes and no, nothing stored, numbers and text as given", () => {
    expect(fieldValue({ key: "passed", kind: "bool", value: "true" })).toBe(copy.yes);
    expect(fieldValue({ key: "passed", kind: "bool", value: "false" })).toBe(copy.no);
    expect(fieldValue({ key: "order", kind: "number", value: null })).toBe(copy.none);
    expect(fieldValue({ key: "time_factor", kind: "number", value: "1.5" })).toBe("1,5");
    expect(fieldValue({ key: "text", kind: "text", value: "Jeg bestilte mye." })).toBe("Jeg bestilte mye.");
  });

  it("reads a time in Europe/Oslo", () => {
    expect(fieldValue({ key: "at", kind: "datetime", value: "2026-11-24T09:00:00Z" })).toContain("10:00");
  });

  it("names a row and where it belongs", () => {
    expect(fieldLabel("order")).toBe(copy.fields.order);
    const item = { kind: "week", class_name: "class-of-1994", session_number: 2, at: null, fields: [] };
    expect(itemHeading(item)).toEqual({ kind: copy.kinds.week, context: "class-of-1994, Klasseøkt 2" });
    expect(itemHeading({ ...item, class_name: null, session_number: null }).context).toBeNull();
  });
});

describe("«Mine data» live (Story 15.1)", () => {
  it("reads again on the User's own event", () => {
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(myDataKey);
  });

  it("never reads a prototype name as a label", () => {
    expect(fieldValue({ key: "status", kind: "code", value: "constructor" })).toBe("constructor");
    expect(fieldLabel("toString")).toBe("toString");
  });
});
