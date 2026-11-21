/**
 * Unsent input (AD-10, Story 6.12): what a User has typed and not yet sent, kept in this browser's
 * `localStorage` under the User and the field, so a reload, a page left or an ended session does
 * not lose it. A draft is only ever put back into its field; nothing here sends anything. «Logg
 * ut» clears every draft (`clearAllDrafts`); an expired session keeps them for the same User's
 * next login. Storage can be missing or refuse (a private window, blocked site data): every access
 * is guarded, and the field then simply starts empty. Reused by Epics 9 and 11.
 */

const PREFIX = "olspillet:draft:";

const keyOf = (userId: string, field: string) => `${PREFIX}${userId}:${field}`;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The kept text of `field` for `userId`, or null. */
export function loadDraft(userId: string, field: string): string | null {
  try {
    return storage()?.getItem(keyOf(userId, field)) ?? null;
  } catch {
    return null;
  }
}

/** Keep `value` for `field`; an empty value removes the draft. */
export function saveDraft(userId: string, field: string, value: string): void {
  try {
    const store = storage();
    if (!store) return;
    if (value === "") store.removeItem(keyOf(userId, field));
    else store.setItem(keyOf(userId, field), value);
  } catch {
    // Not kept: the field still works.
  }
}

export function clearDraft(userId: string, field: string): void {
  saveDraft(userId, field, "");
}

function keysWhere(match: (key: string) => boolean): string[] {
  const store = storage();
  if (!store) return [];
  const keys: string[] = [];
  for (let i = 0; i < store.length; i += 1) {
    const key = store.key(i);
    if (key !== null && match(key)) keys.push(key);
  }
  return keys;
}

/** Remove the User's drafts whose field starts with `fieldPrefix`, except the field `keep`. */
export function clearDrafts(userId: string, fieldPrefix: string, keep?: string): void {
  try {
    const store = storage();
    const start = keyOf(userId, fieldPrefix);
    const kept = keep === undefined ? null : keyOf(userId, keep);
    for (const key of keysWhere((k) => k.startsWith(start) && k !== kept)) store?.removeItem(key);
  } catch {
    // Nothing removed: stale drafts are only ever restored into their own field.
  }
}

/** Every draft of every User on this browser («Logg ut»). */
export function clearAllDrafts(): void {
  try {
    const store = storage();
    for (const key of keysWhere((k) => k.startsWith(PREFIX))) store?.removeItem(key);
  } catch {
    // Storage refused: nothing was kept that could be removed.
  }
}
