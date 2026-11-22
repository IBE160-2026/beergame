import { describe, expect, it } from "vitest";

import type { GameWeeks, OverviewGame } from "./api";
import {
  bandMessagePath,
  bandSaid,
  bandText,
  groupsOf,
  type OverviewAlert,
  tableRows,
  waitingElsewhere,
  wallGroups,
} from "./overview";

/** The Varselbånd and the rows' «Melding» (Story 7.11, UX-DR41, UX-DR45): everything is the api's
 * `alert`; the page only words it (AD-10). */
const SESSION = "11111111-1111-1111-1111-111111111111";
const now = Date.parse("2026-11-21T12:00:00Z");

const alert: NonNullable<OverviewAlert> = {
  game_id: "g2",
  game_number: 2,
  role: "wholesaler",
  name: "Noah",
  user_id: "u-noah",
  since: "2026-11-20T13:00:00Z",
};

function game(number: number, status: OverviewGame["status"], since?: string): OverviewGame {
  return {
    game_id: `g${number}`,
    game_number: number,
    status,
    week: 4,
    version: 1,
    chain_cost: null,
    wait_started_at: since ?? null,
    waiting_for: since ? [{ role: "retailer", name: "Ida", since }] : [],
    seats: [],
  };
}

describe("the Varselbånd", () => {
  it("reads «Spill 2 venter på Noah (Grossist) i 23 t.», by Role for a Student no longer in the Class", () => {
    expect(bandText(alert, now)).toBe("Spill 2 venter på Noah (Grossist) i 23 t.");
    expect(bandText({ ...alert, name: null, user_id: null }, now)).toBe("Spill 2 venter på Grossist i 23 t.");
  });

  it("counts down to the api's due time on the server's clock (Story 8.3): «KI overtar om 1 t.», then «nå»", () => {
    const due = (ms: number) => ({ ...alert, takeover_due_at: new Date(now + ms).toISOString() });
    expect(bandText(due(60 * 60_000), now)).toBe("Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 1 t.");
    expect(bandText(due(59 * 60_000 + 59_000), now)).toBe("Spill 2 venter på Noah (Grossist) i 23 t. KI overtar om 59 min.");
    expect(bandText(due(30_000), now)).toMatch(/ KI overtar om under 1 min\.$/);
    expect(bandText(due(0), now)).toBe("Spill 2 venter på Noah (Grossist) i 23 t. KI overtar nå.");
    expect(bandText(due(-20_000), now)).toBe("Spill 2 venter på Noah (Grossist) i 23 t. KI overtar nå.");
    // No due time from the api: the wait alone, as in Story 7.11.
    expect(bandText({ ...alert, takeover_due_at: null }, now)).toBe(bandText(alert, now));
    // The announcement never carries the countdown.
    expect(bandSaid(due(60 * 60_000))).toBe(bandSaid(alert));
  });

  it("announces the game and Student without the ticking duration, and nothing without a band", () => {
    expect(bandSaid(alert)).toBe("Spill 2 venter på Noah (Grossist).");
    expect(bandSaid(null)).toBe("");
  });

  it("presets «Send Melding» to the Student waited for, else to the Class game", () => {
    expect(bandMessagePath(SESSION, alert)).toBe(`/klasseokter/${SESSION}/melding?spill=g2&student=u-noah`);
    expect(bandMessagePath(SESSION, { ...alert, user_id: null })).toBe(`/klasseokter/${SESSION}/melding?spill=g2`);
  });
});

describe("rows with «Melding» and the band's tint", () => {
  const groups = groupsOf([
    game(2, "waiting", "2026-11-20T13:00:00Z"),
    game(5, "waiting", "2026-11-21T10:00:00Z"),
    game(7, "not_started"),
  ]);
  const weeks = new Map<string, { data?: GameWeeks; failed: boolean }>();
  const actions = { sessionId: SESSION, alertId: "g2" };

  it("gives every wall and table row a «Melding» to its Class game and tints only the band's game", () => {
    const wall = wallGroups(groups, weeks, "factory", now, "net", actions).flatMap((group) => group.rows);
    const table = tableRows(groups, weeks, "factory", now, "net", actions);
    for (const rows of [wall, table]) {
      expect(rows.map((row) => [row.id, row.tint])).toEqual([
        ["g2", true],
        ["g5", false],
        ["g7", false],
      ]);
      expect(rows[2]!.link).toEqual({
        href: `/klasseokter/${SESSION}/melding?spill=g7`,
        text: "Melding",
        name: "Melding til alle i Spill 7",
      });
    }
  });

  it("draws no link or tint where the caller offers none (the Landing's wall)", () => {
    const [row] = wallGroups(groups, weeks, "factory", now).flatMap((group) => group.rows);
    expect(row!.link).toBeUndefined();
    expect(row!.tint).toBeUndefined();
  });

  it("leaves the band's game out of «Venter ellers»", () => {
    expect(waitingElsewhere(groups, now, "g2").map((row) => row.id)).toEqual(["g5"]);
    expect(waitingElsewhere(groups, now).map((row) => row.id)).toEqual(["g2", "g5"]);
  });
});
