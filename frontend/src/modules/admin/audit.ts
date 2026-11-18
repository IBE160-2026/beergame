import { nb } from "@/copy/nb";

import type { AuditEvent, AuditTarget } from "./api";

const copy = nb.admin.audit;
const MONTHS = nb.admin.users.invitations.months;

/** Change fields not shown: the id is already shown as what the action concerns. */
const HIDDEN_FIELDS = new Set(["resent_invitation_id"]);

/** «18. nov. 2026 kl. 13:01» in Europe/Oslo. */
export function formatTime(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/Oslo",
  }).formatToParts(new Date(iso));
  const part = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return copy.at(
    `${Number(part("day"))}. ${MONTHS[Number(part("month")) - 1]} ${part("year")}`,
    `${part("hour")}:${part("minute")}`,
  );
}

/** The action's name from `nb.ts`; an action with no entry yet shows its code. */
export function actionLabel(action: string): string {
  return Object.hasOwn(copy.actions, action) ? copy.actions[action] : action;
}

/** «Systemet» for a row with no actor, the actor's name now, or «Ukjent». */
export function actorText(event: Pick<AuditEvent, "actor_id" | "actor_name">): string {
  if (event.actor_id === null) return copy.system;
  return event.actor_name ?? copy.unknown;
}

/** What the action concerns, worded by its key; an unknown key or id is «Ukjent». */
export function targetText(target: AuditTarget): string {
  if (target.label === null) return copy.unknown;
  return Object.hasOwn(copy.targets, target.key) ? copy.targets[target.key](target.label) : target.label;
}

function valueText(key: string, value: unknown): string {
  if (value === null || value === undefined) return copy.noChange;
  if (typeof value === "boolean") return value ? copy.values.yes : copy.values.no;
  if (Array.isArray(value)) return String(value.length);
  if (typeof value === "string") {
    if (key === "role" && Object.hasOwn(copy.values.roles, value)) return copy.values.roles[value];
    if (key === "account" && Object.hasOwn(copy.values.account, value)) return copy.values.account[value];
    return value;
  }
  if (typeof value === "number") return String(value);
  return JSON.stringify(value);
}

const FIELD_ORDER = Object.keys(copy.fields);
const fieldRank = (key: string) => (FIELD_ORDER.includes(key) ? FIELD_ORDER.indexOf(key) : FIELD_ORDER.length);

/** The change as labelled lines: the fields of `nb.ts` in its order (the database keeps no key
 * order, so «Gammelt navn» would not reliably come before «Nytt navn»), then the rest. A field
 * with no entry in `nb.ts` shows its own key and value, so an action of a later epic renders with
 * no change here. */
export function changeLines(change: Record<string, unknown>): { label: string; value: string }[] {
  return Object.entries(change)
    .filter(([key]) => !HIDDEN_FIELDS.has(key))
    .sort(([a], [b]) => fieldRank(a) - fieldRank(b))
    .map(([key, value]) => ({
      label: Object.hasOwn(copy.fields, key) ? copy.fields[key] : key,
      value: valueText(key, value),
    }));
}

/** The reason under «Til og med» when the range ends before it starts. ISO dates compare as text. */
export function rangeError(since: string, until: string): string | undefined {
  return since && until && until < since ? copy.filters.rangeReversed : undefined;
}
