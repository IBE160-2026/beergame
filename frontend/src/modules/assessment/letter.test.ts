import { describe, expect, it } from "vitest";

import { boundsBody, boundsChanged, boundsDraftOf, boundsProblem, boundsText, offendingBounds } from "./letter";

const DEFAULTS = { A: 90, B: 80, C: 60, D: 50, E: 40 };

describe("the Indicative letter bounds (Story 12.6)", () => {
  it("drafts, checks and sends the bounds as the api judges them", () => {
    const draft = boundsDraftOf(DEFAULTS);
    expect(draft).toEqual({ A: "90", B: "80", C: "60", D: "50", E: "40" });
    expect(boundsProblem(draft)).toBeUndefined();
    expect(boundsBody({ ...draft, A: " 95 " })).toEqual({ ...DEFAULTS, A: 95 });
  });

  it("refuses bounds outside 1 to 100, not whole, or not strictly falling", () => {
    const draft = boundsDraftOf(DEFAULTS);
    for (const bad of ["0", "101", "9,5", "", "-1", "1e2"]) {
      expect(boundsProblem({ ...draft, C: bad })).toBe("out_of_range");
    }
    expect(boundsProblem({ ...draft, B: "90" })).toBe("out_of_order");
    expect(boundsProblem({ ...draft, E: "55" })).toBe("out_of_order");
  });

  it("names the bounds the problem is in, so those fields carry the error", () => {
    const draft = boundsDraftOf(DEFAULTS);
    expect([...offendingBounds(draft)]).toEqual([]);
    expect([...offendingBounds({ ...draft, B: "95" })]).toEqual(["B"]);
    expect([...offendingBounds({ ...draft, E: "55" })]).toEqual(["E"]);
    expect([...offendingBounds({ ...draft, C: "x" })]).toEqual(["C"]);
  });

  it("sends only a changed set", () => {
    expect(boundsChanged(boundsDraftOf(DEFAULTS), DEFAULTS)).toBe(false);
    expect(boundsChanged({ ...boundsDraftOf(DEFAULTS), D: "55" }, DEFAULTS)).toBe(true);
  });

  it("reads the bounds as text once they are read-only", () => {
    expect(boundsText(DEFAULTS)).toBe("A fra 90 %, B fra 80 %, C fra 60 %, D fra 50 %, E fra 40 %");
  });
});
