import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { draftOf, judgeDraft, parseWeight, type QuestionSet } from "./api";

const item = (id: string, weight: number, quantity = false) => ({
  id,
  type: "number" as const,
  title: id,
  weight,
  default_weight: weight,
  excluded: false,
  quantity,
  starting_task: false,
});

const SET: QuestionSet = {
  version: 1,
  draft: true,
  outdated: false,
  pinned: false,
  open: true,
  can_change: true,
  items: [item("a", 40, true), item("b", 30)],
  adapted: { weight: 30, default_weight: 30, replacements: 2 },
  sum: 100,
};

describe("«Spørsmål og vekter» (Story 11.1)", () => {
  it("takes only whole numbers from 0 to 100, the values the api accepts", () => {
    expect(["0", "100", " 7 ", "05"].map(parseWeight)).toEqual([0, 100, 7, 5]);
    expect(["", "101", "-1", "2.5", "1e2", "abc"].map(parseWeight)).toEqual([null, null, null, null, null, null]);
  });

  it("sums the items left in and the Adapted total, live", () => {
    const draft = draftOf(SET);
    expect(judgeDraft(SET, draft)).toMatchObject({ sum: 100, quantityOut: false });
    const out = judgeDraft(SET, { ...draft, excluded: new Set(["a"]) });
    expect(out).toMatchObject({ sum: 60, quantityOut: true });
    expect(out.body).toEqual({ weights: { a: 40, b: 30 }, excluded: ["a"], adapted_weight: 30 });
    expect(nb.tests.questionSet.sum(95)).toBe("Sum 95 %. Vektene må bli 100 %.");
    expect(nb.tests.questionSet.sum(100)).toBe("Sum 100 %.");
  });

  it("counts a weight the api would refuse as nothing and sends no body", () => {
    const judged = judgeDraft(SET, { ...draftOf(SET), weights: { a: "x", b: "30" } });
    expect(judged.sum).toBe(60);
    expect([...judged.invalid]).toEqual(["a"]);
    expect(judged.body).toBeNull();
    // A taken-out item's field does not block.
    const out = judgeDraft(SET, { version: 1, weights: { a: "x", b: "70" }, excluded: new Set(["a"]), adapted: "30" });
    expect(out.invalid.size).toBe(0);
    expect(out.body?.weights.a).toBe(40);
  });
});
