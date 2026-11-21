import { describe, expect, it } from "vitest";

import { ANNOUNCE_EVERY_MS, announceIn } from "./announce";

const MINUTE = ANNOUNCE_EVERY_MS;

describe("announceIn", () => {
  it("says nothing for the value the page opened with", () => {
    expect(announceIn("1 venter", "1 venter", null, 0, MINUTE)).toBeNull();
  });

  it("says the first change at once", () => {
    expect(announceIn("2 venter", "1 venter", null, 5_000, MINUTE)).toBe(0);
  });

  it("holds a later change until a minute after the last one said", () => {
    const said = { text: "2 venter", at: 10_000 };
    expect(announceIn("3 venter", "1 venter", said, 30_000, MINUTE)).toBe(40_000);
    expect(announceIn("3 venter", "1 venter", said, 70_000, MINUTE)).toBe(0);
    expect(announceIn("3 venter", "1 venter", said, 90_000, MINUTE)).toBe(0);
  });

  it("does not say again what was last said, even after a change back and forth", () => {
    expect(announceIn("2 venter", "1 venter", { text: "2 venter", at: 0 }, 30_000, MINUTE)).toBeNull();
  });
});
