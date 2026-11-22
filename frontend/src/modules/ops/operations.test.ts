import { describe, expect, it } from "vitest";

import { barPercent, fallbackName, hourAxisTop, hourText, hourTotal, msText, shareText } from "./operations";

const NBSP = " ";
const GROUP = " ";

const hour = (iso: string, c: number, j: number, a: number) => ({
  hour: iso,
  conservation_check: c,
  job_failed: j,
  api_error: a,
});

describe("«Drift» figures (Story 15.8)", () => {
  it("labels an hour's start in Oslo time, winter and summer", () => {
    expect(hourText("2026-11-19T09:00:00Z")).toBe("10");
    expect(hourText("2026-06-19T09:00:00Z")).toBe("11");
    expect(hourText("2026-11-18T23:00:00Z")).toBe("00");
  });

  it("sums an hour and puts the axis top at the busiest hour, at least 1", () => {
    const hours = [hour("2026-11-19T08:00:00Z", 1, 2, 3), hour("2026-11-19T09:00:00Z", 0, 0, 1)];
    expect(hourTotal(hours[0])).toBe(6);
    expect(hourAxisTop(hours)).toBe(6);
    expect(hourAxisTop([hour("2026-11-19T09:00:00Z", 0, 0, 0)])).toBe(1);
    expect(hourAxisTop([])).toBe(1);
  });

  it("draws bars as a share of the axis, never past it", () => {
    expect(barPercent(3, 6)).toBe("50%");
    expect(barPercent(0, 6)).toBe("0%");
    expect(barPercent(9, 6)).toBe("100%");
    expect(barPercent(1, 0)).toBe("0%");
  });

  it("writes shares, times and kinds in Norwegian", () => {
    expect(shareText("0.2222")).toBe(`22,22${NBSP}%`);
    expect(shareText("0.5000")).toBe(`50${NBSP}%`);
    expect(shareText(null)).toBe("–");
    expect(msText(1250)).toBe(`1${GROUP}250${NBSP}ms`);
    expect(fallbackName("fallback_timeout")).toBe("Tidsavbrudd");
    expect(fallbackName("unknown")).toBe("unknown");
  });
});
