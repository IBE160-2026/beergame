import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import { copyLines, sourceGroups, sourceLabel } from "./rerun";

const r = nb.sessions.list.rerun;
const LEVELS = [
  { name: "standard", label: "Standard" },
  { name: "careful", label: null },
];

describe("sourceLabel and sourceGroups", () => {
  const source = (id: string, classId: string, number: number, archived = false) => ({
    id,
    class_id: classId,
    class_name: `klasse-${classId}`,
    number,
    start_at: null,
    archived,
  });

  it("names the number and the Start date in Europe/Oslo, or that there is none", () => {
    expect(sourceLabel({ number: 2, start_at: "2025-11-24T09:00:00Z" })).toBe(
      `Klasseøkt 2, ${r.started("ma. 24. nov. kl.\u00a010:00")}`,
    );
    expect(sourceLabel({ number: 1, start_at: null })).toBe(r.option(1, r.noStart));
  });

  it("groups the sources by Class in the api's order and marks an archived Class", () => {
    const groups = sourceGroups([source("c", "b", 1), source("b", "a", 2, true), source("a", "a", 1, true)]);
    expect(groups.map((g) => [g.label, g.items.map((i) => i.id)])).toEqual([
      ["klasse-b", ["c"]],
      ["klasse-a (arkivert)", ["b", "a"]],
    ]);
  });
});

describe("copyLines", () => {
  const copied = { class_name: "class-of-1994", number: 3 };

  it("names the source and a replaced Effort level by their labels until the first save", () => {
    const item = {
      saved_at: null,
      copied_from: copied,
      effort_level_replaced: { name: "careful", label: "Grundig" },
      effort_level: "standard",
      effort_levels: LEVELS,
    };
    expect(copyLines(item)).toEqual([
      nb.sessions.copied.from(3, "class-of-1994"),
      nb.sessions.copied.levelReplaced("Grundig", "Standard"),
    ]);
    expect(copyLines({ ...item, saved_at: "2026-11-20T10:00:00Z" })).toEqual([]);
  });

  it("falls back to the level names and says nothing for a session that is no copy", () => {
    const item = {
      copied_from: null,
      effort_level_replaced: { name: "gone", label: null },
      effort_level: "careful",
      effort_levels: LEVELS,
    };
    expect(copyLines(item)).toEqual([nb.sessions.copied.levelReplaced("gone", "careful")]);
    expect(copyLines({ copied_from: null, effort_level_replaced: null, effort_levels: [] })).toEqual([]);
  });
});
