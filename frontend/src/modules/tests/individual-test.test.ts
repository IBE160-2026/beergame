import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";
import { stepItems } from "@/modules/games/home";
import type { EnrolledSession } from "@/modules/sessions/api";

import { type MyTest, myTestKey, myTestsKey } from "./api";
import { deadlineLine, itemLines, testView } from "./individual-test";

const copy = nb.tests.individual;

const statement: MyTest = { state: "statement", test_deadline: "2026-12-18T22:59:00Z", opened_at: null, items: [] };

describe("the Individual test page's state (Story 11.3)", () => {
  it("follows the api's answer and refusals alone", () => {
    expect(testView(statement, null)).toBe("statement");
    expect(testView({ ...statement, state: "open" }, null)).toBe("open");
    expect(testView({ ...statement, state: "closed" }, null)).toBe("closed");
    expect(testView(undefined, "replay_required")).toBe("locked");
    expect(testView(undefined, "forbidden")).toBe("denied");
    expect(testView(undefined, null)).toBe("other");
  });

  it("says the Testfrist in Oslo time, and nothing without one", () => {
    // The shared date text keeps «kl.» and the time together with a non-breaking space.
    expect(deadlineLine(statement)).toMatch(/^Testfrist fr\. 18\. des\. kl\.\s23:59\.$/u);
    expect(deadlineLine({ test_deadline: null })).toBeNull();
  });

  it("numbers the items and names their type in words", () => {
    expect(itemLines({ number: 3, type: "long" })).toEqual({ heading: "Oppgave 3", type: "Langsvar" });
    expect(itemLines({ number: 1, type: "table" }).type).toBe(copy.types.table);
  });

  it("is read again on the User's `user` event", () => {
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(myTestsKey);
    expect(myTestKey("s1").slice(0, 2)).toEqual([...myTestsKey]);
  });
});

describe("Stegene's Individual test step (Story 11.3)", () => {
  const flags = { held: false, quiz_changed: false, group_open: false, closed: false };
  const steps = (state: "current" | "locked"): EnrolledSession["steps"] => [
    { step: "replay", state: state === "current" ? "done" : "current", ...flags },
    { step: "test", state, ...flags },
  ];

  it("leads to the test page while it is the current step", () => {
    const [, test] = stepItems(steps("current"), "s 1");
    expect(test.href).toBe("/individuell-test/s%201");
    expect(test.note).toBe(nb.homes.student.current);
  });

  it("says when it opens while locked, with no link", () => {
    const [, test] = stepItems(steps("locked"), "s1");
    expect(test.href).toBeUndefined();
    expect(test.note).toBe("Individuell test, åpnes når du har fullført Replay.");
  });
});
