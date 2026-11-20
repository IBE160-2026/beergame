import { nb } from "@/copy/nb";

import { osloDateText } from "./dates";

const copy = nb.sessions.list.rerun;

type Source = { id: string; class_id: string; class_name: string; number: number; start_at?: string | null; archived: boolean };

/** «Klasseøkt 2, start ti. 24. nov. kl. 10:00» (Story 5.18): an option under its Class's group. */
export function sourceLabel(source: Pick<Source, "number" | "start_at">): string {
  const start = source.start_at ? copy.started(osloDateText(source.start_at)) : copy.noStart;
  return copy.option(source.number, start);
}

/** The sources grouped by Class, in the order the api gave them (newest first), each group named
 * by its Class with «(arkivert)» for an archived one: short options that fit a phone. */
export function sourceGroups<T extends Source>(sources: readonly T[]): { classId: string; label: string; items: T[] }[] {
  const groups = new Map<string, { classId: string; label: string; items: T[] }>();
  for (const source of sources) {
    const group = groups.get(source.class_id) ?? {
      classId: source.class_id,
      label: copy.group(source.class_name, source.archived),
      items: [],
    };
    group.items.push(source);
    groups.set(source.class_id, group);
  }
  return [...groups.values()];
}

type Copied = {
  saved_at?: string | null;
  copied_from?: { class_name: string; number: number } | null;
  effort_level_replaced?: { name: string; label?: string | null } | null;
  effort_level?: string | null;
  effort_levels: readonly { name: string; label?: string | null }[];
};

/** What the Klasseøkt says of a copy until it is first saved (Story 5.18): its source, and an
 * Effort level the new model did not offer, by its label. Empty for any other session. */
export function copyLines(item: Copied): string[] {
  if (item.saved_at) return [];
  const lines: string[] = [];
  if (item.copied_from) lines.push(nb.sessions.copied.from(item.copied_from.number, item.copied_from.class_name));
  const replaced = item.effort_level_replaced;
  if (replaced) {
    const now = item.effort_levels.find((level) => level.name === item.effort_level);
    lines.push(nb.sessions.copied.levelReplaced(replaced.label ?? replaced.name, now?.label ?? item.effort_level ?? ""));
  }
  return lines;
}
