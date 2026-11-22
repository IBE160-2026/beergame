import { describe, expect, it } from "vitest";

import { GUIDE_TEXT_MAX, guideBody, guideTextProblem, type ScoringGuide } from "./api";

const question = (id: string, guide: string) => ({
  id,
  kind: "long" as const,
  title: id,
  guide,
  standard_guide: guide,
  changed: false,
  criteria: [{ code: "F1", text: "Kriterium", weight: 100 }],
});

const GUIDE: ScoringGuide = {
  version_id: "01a1f9a0-0000-7000-8000-000000000122",
  version: 1,
  draft: true,
  edited: false,
  outdated: false,
  checked: false,
  pinned: false,
  open: true,
  can_change: true,
  scale: [0, 1, 2, 3, 4].map((step) => ({ step, label: `Steg ${step}` })),
  questions: [question("a", "Tekst a"), question("b", "Tekst b")],
};

describe("guideBody", () => {
  it("sends only the touched texts that differ from the guide in force", () => {
    expect(guideBody(GUIDE, {})).toBeNull();
    expect(guideBody(GUIDE, { a: "Tekst a" })).toBeNull();
    expect(guideBody(GUIDE, { a: "Ny a", b: "Tekst b" })).toEqual({ guides: { a: "Ny a" } });
  });

  it("sends nothing while a touched text is empty or too long", () => {
    expect(guideBody(GUIDE, { a: "Ny a", b: "  " })).toBeNull();
    expect(guideBody(GUIDE, { a: "x".repeat(GUIDE_TEXT_MAX + 1) })).toBeNull();
  });
});

describe("guideTextProblem", () => {
  it("names an empty and a too long text", () => {
    expect(guideTextProblem("")).toBe("empty");
    expect(guideTextProblem(" \n ")).toBe("empty");
    expect(guideTextProblem("x".repeat(GUIDE_TEXT_MAX))).toBeNull();
    expect(guideTextProblem("x".repeat(GUIDE_TEXT_MAX + 1))).toBe("tooLong");
  });
});
