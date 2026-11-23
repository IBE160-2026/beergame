import { describe, expect, it } from "vitest";

import { dailySpendPath, dayText, dayUsdText, parseDay, shiftDay } from "./daily-spend";

describe("the day of «KI-kostnad per dag»", () => {
  it("reads only a real calendar day from ?dag=", () => {
    expect(parseDay("2026-11-19")).toBe("2026-11-19");
    expect(parseDay("2026-02-29")).toBeUndefined();
    expect(parseDay("2026-13-01")).toBeUndefined();
    expect(parseDay("19.11.2026")).toBeUndefined();
    expect(parseDay(null)).toBeUndefined();
  });

  it("steps across month and year ends", () => {
    expect(shiftDay("2026-11-30", 1)).toBe("2026-12-01");
    expect(shiftDay("2027-01-01", -1)).toBe("2026-12-31");
    expect(shiftDay("2026-03-29", -1)).toBe("2026-03-28"); // the summer-time night
  });

  it("names the day, its link and its amounts", () => {
    expect(dayText("2026-11-19")).toBe("19. nov. 2026");
    expect(dailySpendPath("2026-11-19")).toBe("/admin/ki-kostnad?dag=2026-11-19");
    expect(dayUsdText("1234.505")).toBe("1 234,51 USD");
    expect(dayUsdText("0.00000000")).toBe("0,00 USD");
  });
});
