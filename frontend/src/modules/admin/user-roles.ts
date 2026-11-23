import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import type { AccountRole, ListedUser } from "./api";

const copy = nb.admin.users.list;

/** The account roles a button can grant or revoke, in the order the buttons stand. */
export const ROLES: readonly AccountRole[] = ["lecturer", "admin"];

/** The first word of a User's name, as the buttons and lines address them («Bård»). */
export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] || name;
}

export function holds(user: ListedUser, role: AccountRole): boolean {
  return user.roles.includes(role);
}

/** The roles cell: «Faglærer, Admin», or «Ingen rolle». */
export function rolesText(user: ListedUser): string {
  const held = ROLES.filter((role) => holds(user, role)).map((role) => copy.roles[role]);
  return held.length ? held.join(", ") : copy.noRole;
}

/** The button's label states its effect and the User: «Gi Bård rollen Faglærer» or «Fjern
 * rollen Faglærer fra Bård». */
export function roleButtonLabel(user: ListedUser, role: AccountRole): string {
  const name = firstName(user.name);
  return holds(user, role) ? copy.revoke(name, copy.roles[role]) : copy.grant(name, copy.roles[role]);
}

/** The line after a change: «Bård har nå rollen Faglærer.» */
export function changedLine(user: ListedUser, role: AccountRole, granted: boolean): string {
  const name = firstName(user.name);
  return granted ? copy.granted(name, copy.roles[role]) : copy.revoked(name, copy.roles[role]);
}

/** The line for a refused change: the blocked revoke with the real count, the last Admin, or
 * the general line. */
export function refusalLine(error: unknown, user: ListedUser): string {
  const name = firstName(user.name);
  if (error instanceof ApiRequestError) {
    if (error.code === "role_revoke_blocked") {
      const classes = Number(error.fields.classes);
      if (Number.isInteger(classes) && classes > 0) return copy.blocked(name, classes);
    }
    if (error.code === "last_admin") return copy.lastAdmin(name);
  }
  return copy.failed;
}

/** The status button states its effect: «Deaktiver Bård. Bård kan ikke logge inn, og dataene
 * blir værende.» or «Aktiver Bård igjen» (Story 3.10, UX-DR57). */
export function statusButtonLabel(user: ListedUser): string {
  const name = firstName(user.name);
  return user.is_active ? copy.deactivate(name) : copy.reactivate(name);
}

/** The line after a status change, from the answer: «Bård er deaktivert.» */
export function statusChangedLine(user: ListedUser): string {
  const name = firstName(user.name);
  return user.is_active ? copy.reactivatedLine(name) : copy.deactivatedLine(name);
}

/** The line for a refused status change: oneself, the last Admin, or the general line. */
export function statusRefusalLine(error: unknown, user: ListedUser, selfId: string): string {
  if (error instanceof ApiRequestError && error.code === "last_admin") {
    return user.id === selfId ? copy.deactivateSelf : copy.lastAdmin(firstName(user.name));
  }
  return copy.statusFailed;
}

/** The longest reference the api takes (`DELETE_REFERENCE_MAX_LENGTH` in `identity/schemas.py`). */
export const DELETE_REFERENCE_MAX_LENGTH = 200;

/** The reference as the api stores it: trimmed, inner whitespace collapsed. */
export function deleteReference(typed: string): string {
  return typed.split(/\s+/).filter(Boolean).join(" ");
}

/** A reference checked before it is sent: the reason the field shows, or undefined. The api
 * decides, and also refuses one that names the User. */
export function deleteReferenceError(typed: string): string | undefined {
  const reference = deleteReference(typed);
  const errors = copy.delete.errors;
  if (!reference) return errors.reference_empty;
  if (reference.length > DELETE_REFERENCE_MAX_LENGTH) return errors.reference_too_long;
  if (reference.includes("@") || /\p{Cc}/u.test(reference)) return errors.reference_invalid;
  return undefined;
}

/** A refused deletion (Story 15.2): `field` is the reason beside the reference field, `line` the
 * row's line (the blocked owner with the real count, oneself, the last Admin, or the general
 * line). */
export function deleteRefusal(error: unknown, user: ListedUser, selfId: string): { field?: string; line?: string } {
  const name = firstName(user.name);
  if (error instanceof ApiRequestError) {
    const reason = error.fields.reference;
    if (typeof reason === "string" && copy.delete.errors[reason]) return { field: copy.delete.errors[reason] };
    if (error.code === "role_revoke_blocked") {
      const classes = Number(error.fields.classes);
      if (Number.isInteger(classes) && classes > 0) return { line: copy.blocked(name, classes) };
    }
    if (error.code === "last_admin") return { line: user.id === selfId ? copy.delete.self : copy.lastAdmin(name) };
  }
  return { line: copy.delete.failed };
}
