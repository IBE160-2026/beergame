import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { consentDay, decisionLine } from "./test-student-consent";

describe("A test student's consent on Hjem (Story 12.8)", () => {
  it("reads no line before a decision, the day once consent is given, and the decline's line", () => {
    expect(decisionLine(undefined)).toBeNull();
    expect(decisionLine({ decision: null, text_version: "v", decided_at: null })).toBeNull();
    expect(consentDay("2026-11-22T23:30:00Z")).toBe("23. november");
    expect(decisionLine({ decision: "given", text_version: "v", decided_at: "2026-11-23T09:00:00Z" })).toBe(
      nb.homes.consent.given("23. november"),
    );
    expect(decisionLine({ decision: "declined", text_version: "v", decided_at: "2026-11-23T09:00:00Z" })).toBe(
      nb.homes.consent.declined,
    );
  });
});
