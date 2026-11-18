import { describe, expect, it } from "vitest";

import { formatClock } from "./connection";

describe("formatClock", () => {
  it("gives the Oslo clock time with a colon, in winter and in summer", () => {
    expect(formatClock(Date.UTC(2026, 10, 18, 20, 14))).toBe("21:14");
    expect(formatClock(Date.UTC(2026, 6, 1, 6, 5))).toBe("08:05");
    expect(formatClock(Date.UTC(2026, 0, 1, 23, 0))).toBe("00:00");
  });
});
