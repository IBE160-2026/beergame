import { describe, expect, it } from "vitest";

import type { ConnectionBudget, ProcessConnections } from "./api";
import { configuredText, poolerText, runningText } from "./connection-budget";

const counts = (total: number) => ({
  sqlalchemy_pool: total - 1,
  procrastinate_pool: 0,
  listen: 1,
  total,
});

const process = (configured: number | null, over = false): ProcessConnections => ({
  process: "backend",
  budget: counts(11),
  configured: configured === null ? null : counts(configured),
  reported_at: configured === null ? null : "2026-11-22T10:00:00Z",
  over_budget: over,
});

const budget = (changes: Partial<ConnectionBudget>): ConnectionBudget => ({
  read_at: "2026-11-22T10:00:00Z",
  processes: [],
  budget_total: 25,
  overlap_total: 50,
  configured_total: 25,
  running: "within",
  pooler: { status: "not_checked", pooler_size: null, required: 51 },
  ...changes,
});

describe("«Databasetilkoblinger» (Story 15.9)", () => {
  it("shows what a process set aside, marks it over its line, and names a missing report", () => {
    expect(configuredText(process(11))).toBe("11");
    expect(configuredText(process(21, true))).toBe("21, over budsjettet");
    expect(configuredText(process(null))).toBe("Ikke rapportert");
  });

  it("states the running sum against the budget for each state", () => {
    expect(runningText(budget({}))).toContain("innenfor budsjettet: 25 av 25");
    expect(runningText(budget({ running: "over", configured_total: 30 }))).toContain(
      "satt av 30 tilkoblinger, budsjettet er 25",
    );
    expect(runningText(budget({ running: "incomplete", configured_total: 11 }))).toContain(
      "11 av 25 tilkoblinger er rapportert",
    );
  });

  it("gives both numbers of the pooler check and never calls an unset size a pass", () => {
    const failed = budget({
      pooler: { status: "failed", pooler_size: 15, required: 51 },
    });
    expect(poolerText(failed)).toBe("Pooleren er for liten: den har plass til 15 tilkoblinger, behovet er 51.");
    const passed = budget({
      pooler: { status: "passed", pooler_size: 60, required: 51 },
    });
    expect(poolerText(passed)).toBe("Pooleren rommer en utrulling: den har plass til 60 tilkoblinger, behovet er 51.");
    const unset = poolerText(budget({}));
    expect(unset).toBe("Pooleren er ikke sjekket: størrelsen på pooleren er ikke oppgitt. Behovet er 51.");
    expect(unset).not.toContain("rommer");
  });
});
