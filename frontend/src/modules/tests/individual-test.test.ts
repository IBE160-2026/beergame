import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";
import { stepItems } from "@/modules/games/home";
import type { EnrolledSession } from "@/modules/sessions/api";

import { type MyTest, myTestKey, myTestsKey } from "./api";
import { deadlineLine, isAnswered, itemLabel, itemLines, listSeparator, submittedLine, testView, unansweredNumbers } from "./individual-test";

const copy = nb.tests.individual;

const statement: MyTest = {
  state: "statement",
  test_deadline: "2026-12-18T22:59:00Z",
  opened_at: null,
  submitted_at: null,
  items: [],
  server_now: "2026-12-18T20:00:00Z",
  sitting_ended: false,
};

describe("the Individual test page's state (Story 11.3)", () => {
  it("follows the api's answer and refusals alone", () => {
    expect(testView(statement, null)).toBe("statement");
    expect(testView({ ...statement, state: "open" }, null)).toBe("open");
    expect(testView({ ...statement, state: "closed" }, null)).toBe("closed");
    expect(testView({ ...statement, state: "submitted" }, null)).toBe("submitted");
    expect(testView({ ...statement, state: "auto_submitted" }, null)).toBe("auto_submitted");
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
    // Story 11.7: an Adapted item, answered as a long answer.
    expect(itemLines({ number: 12, type: "adapted" })).toEqual({ heading: "Oppgave 12", type: "Tilpasset oppgave" });
  });

  it("marks an Adapted item an LLM worded, and nothing else (Story 11.8)", () => {
    const text = "Utkast: Du var Grossist i Klassespillet. I uke 7 bestilte du 16 enheter.";
    const ai = itemLabel({ title: text, wording: { text, ai_generated: true, llm_call_id: "c" } });
    expect(ai).toEqual({ label: `KI-generert, kan ta feil: «${text}»`, ai: true, note: nb.debrief.aiNote });
    expect(itemLabel({ title: text, wording: { text, ai_generated: false, llm_call_id: null } })).toEqual({ label: text, ai: false, note: null });
    expect(itemLabel({ title: "Utkast: forklar.", wording: null })).toEqual({ label: "Utkast: forklar.", ai: false, note: null });
  });

  it("is read again on the User's `user` event", () => {
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(myTestsKey);
    expect(myTestKey("s1").slice(0, 2)).toEqual([...myTestsKey]);
  });
});

describe("the review before «Lever testen» (Story 11.10)", () => {
  const answer = (value: unknown) => ({ value, revision: 1, saved_at: "2026-12-18T20:40:00Z" });

  it("counts an item answered only when it holds a value to hand in", () => {
    expect(isAnswered({ answer: null })).toBe(false);
    expect(isAnswered({ answer: answer(null) })).toBe(false);
    expect(isAnswered({ answer: answer(" \n ") })).toBe(false);
    expect(isAnswered({ answer: answer([null, null]) })).toBe(false);
    expect(isAnswered({ answer: answer([null, 0]) })).toBe(true);
    expect(isAnswered({ answer: answer(0) })).toBe(true);
    expect(isAnswered({ answer: answer("b") })).toBe(true);
    expect(isAnswered({ answer: answer("Et svar.") })).toBe(true);
  });

  it("lists the numbers not answered as «4, 7 og 9»", () => {
    const items = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((number) => ({ number, answer: [4, 7, 9].includes(number) ? null : answer("a") }));
    const numbers = unansweredNumbers({ items: items as unknown as MyTest["items"] });
    expect(numbers).toEqual([4, 7, 9]);
    const list = numbers.map((n, i) => `${listSeparator(i, numbers.length)}${n}`).join("");
    expect(`${copy.submit.unanswered(numbers.length)} ${list}${copy.submit.listEnd}`).toBe("3 oppgaver er ikke besvart: 4, 7 og 9.");
    expect(`${copy.submit.unanswered(1)} 4${copy.submit.listEnd}`).toBe("1 oppgave er ikke besvart: 4.");
    expect([0, 1].map((i) => listSeparator(i, 2))).toEqual(["", " og "]);
  });

  it("says when the test was handed in, in Oslo time", () => {
    const handedIn = { state: "submitted" as const, submitted_at: "2026-12-18T20:40:00Z" };
    expect(submittedLine(handedIn)).toMatch(/^Levert fr\. 18\. des\. kl\.\s21:40\. Du kan ikke endre svarene\.$/u);
    expect(submittedLine({ state: "auto_submitted", submitted_at: "2026-12-18T22:59:00Z" })).toBe(copy.submit.autoSubmitted);
    expect(submittedLine({ state: "open", submitted_at: null })).toBeNull();
    // Story 11.12: handed in by the sweep when the timed sitting ended.
    expect(submittedLine({ state: "auto_submitted", submitted_at: "2026-12-18T20:00:00Z", sitting_ended: true })).toBe(
      "Tiden er ute. Testen er levert.",
    );
  });
});

describe("Stegene's Individual test step (Story 11.3)", () => {
  const flags = { held: false, quiz_changed: false, group_open: false, closed: false, corrected: false, after_makeup: false };
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
