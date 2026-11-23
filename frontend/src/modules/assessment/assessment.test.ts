import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { topicKeys } from "@/lib/api/topics";
import { assessmentReady, testHandedIn } from "@/modules/games/home";
import { ASSESSMENT_PATH } from "@/modules/identity/homes";
import { myTestsKey } from "@/modules/tests/api";

import { myAssessmentKey } from "./api";
import { numbersText, pointsText, scoreText, stateLine, totalText } from "./assessment";

const copy = nb.assessment.student;

describe("the Student's KI-vurdering (Story 12.2)", () => {
  it("names item numbers in words", () => {
    expect(numbersText([])).toBe("");
    expect(numbersText([3])).toBe("3");
    expect(numbersText([3, 6])).toBe("3 og 6");
    expect(numbersText([2, 3, 6])).toBe("2, 3 og 6");
  });

  it("says one line for each state with nothing to list", () => {
    expect(stateLine({ state: "not_ready", unassessed: [] })).toBe(
      "KI-vurderingen kommer innen ett døgn etter testfristen.",
    );
    expect(stateLine({ state: "switched_off", unassessed: [] })).toBe(
      "Faglærer har slått av KI-vurdering for denne Klasseøkten. Studentrapporten finnes som vanlig.",
    );
    expect(stateLine({ state: "failed", unassessed: [] })).toBe(copy.failed);
    expect(stateLine({ state: "no_test", unassessed: [] })).toBe(copy.noTest);
    expect(stateLine({ state: "incomplete", unassessed: [11, 13] })).toContain("11 og 13");
    expect(stateLine({ state: "ready", unassessed: [] })).toBeNull();
  });

  it("puts every number through the formatter and never a partial total", () => {
    expect(pointsText({ points: 7.5, weight: 10 })).toBe("7,5 av 10 poeng");
    expect(pointsText({ points: null, weight: 15 })).toBe(copy.notAssessed);
    expect(totalText({ total: 57.75, total_max: 100 })).toBe("Vektet sum: 57,75 av 100 poeng");
    expect(totalText({ total: null, total_max: null })).toBeNull();
  });

  it("gives the AI's step with its label, or the computed result, in words", () => {
    const ai = { assessed: true, step: 3, top: 4, label: "Godt", feedback_dropped: false, flagged: false };
    expect(scoreText({ ai, computed: null })).toBe("KI-vurdering: 3 av 4 (Godt)");
    expect(scoreText({ ai: { assessed: false, step: null, top: 4, label: null, feedback_dropped: false, flagged: false }, computed: null })).toBe(copy.notAssessed);
    expect(scoreText({ ai: null, computed: { result: "partly", criteria: [] } })).toBe(copy.computed.partly);
  });

  it("is read again with the Student's tests and linked from Hjem once the test is handed in", () => {
    expect(myAssessmentKey("s1").slice(0, 2)).toEqual([...myTestsKey]);
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(myTestsKey);
    expect(ASSESSMENT_PATH("a b")).toBe("/ki-vurdering/a%20b");
    expect(testHandedIn([{ step: "test", state: "done" }] as never)).toBe(true);
    expect(testHandedIn([{ step: "test", state: "current" }] as never)).toBe(false);
    expect(testHandedIn(undefined as never)).toBe(false);
  });

  it("says on Hjem that it is ready once «Rapport» is done, read again on `user:<id>` (Story 12.4)", () => {
    expect(assessmentReady([{ step: "test", state: "done" }, { step: "report", state: "done" }] as never)).toBe(true);
    expect(assessmentReady([{ step: "test", state: "done" }, { step: "report", state: "current" }] as never)).toBe(false);
    expect(assessmentReady(undefined as never)).toBe(false);
    expect(topicKeys({ topic: "user", id: "u1", version: null })).toContainEqual(["class-sessions", "enrolled"]);
    expect(copy.readyOnHjem).toBe("KI-vurderingen er klar.");
  });
});
