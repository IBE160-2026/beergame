import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { ConnectionBudget, ProcessConnections } from "./api";

const copy = nb.admin.operations.connections;

/** «12» or «12, over budsjettet», or «Ikke rapportert» for a process that never reported. */
export function configuredText(item: ProcessConnections): string {
  if (!item.configured) return copy.notReported;
  const count = formatNumber(item.configured.total);
  return item.over_budget ? copy.over(count) : count;
}

/** The line on the running processes against the budget. */
export function runningText(found: ConnectionBudget): string {
  const configured = formatNumber(found.configured_total);
  const budget = formatNumber(found.budget_total);
  switch (found.running) {
    case "over":
      return copy.running.over(configured, budget);
    case "incomplete":
      return copy.running.incomplete(configured, budget);
    case "within":
      return copy.running.within(configured, budget);
  }
}

/** The pooler check's line, with both numbers; an unset `DB_POOLER_SIZE` is never a pass. */
export function poolerText(found: ConnectionBudget): string {
  const { status, pooler_size: size, required } = found.pooler;
  const need = formatNumber(required);
  if (status === "passed" && size !== null) return copy.pooler.passed(formatNumber(size), need);
  if (status === "failed" && size !== null) return copy.pooler.failed(formatNumber(size), need);
  return copy.pooler.notChecked(need);
}
