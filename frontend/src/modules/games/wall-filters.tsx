"use client";

import { useId } from "react";

import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";
import { roleName } from "@/modules/sessions/sessions";

import type { WallFilter } from "./api";
import type { StatusFilter } from "./overview";
import { measureName } from "./wall-copy";

const copy = nb.wall.filters;

const ROLES: readonly WallFilter["role"][] = ["retailer", "wholesaler", "distributor", "factory"];
const CELLS: readonly WallFilter["cells"][] = ["net", "order", "cost"];
const STATUSES: readonly StatusFilter[] = [
  "all",
  "waiting",
  "paused",
  "running",
  "not_started",
  "finished",
  "with_ai",
];

const STATUS_WORD: Record<StatusFilter, string> = {
  all: copy.all,
  waiting: nb.wall.status.waiting,
  paused: nb.wall.status.paused,
  running: nb.wall.status.running,
  not_started: nb.wall.status.notStarted,
  finished: nb.wall.status.finished,
  with_ai: copy.withAi,
};

type Choice<T extends string> = { value: T; label: string; count?: number };

/**
 * Veggfiltre (`wall-filters`, Story 7.4, UX-DR43): Rolle, Celler and Status above the Matrisevegg,
 * each a row of text buttons with `aria-pressed`, one pressed per group. The pressed one is weight
 * 600 and underlined; Status counts follow in `ink-secondary` («Venter 4»). No pills, no fills.
 * A Status choice shows when it matches a game or is the one pressed; «Alle» always shows. A
 * choice applies at once (the caller filters the rows it holds).
 */
export function WallFilters({
  filter,
  counts,
  onChange,
}: {
  filter: WallFilter;
  counts: Readonly<Record<StatusFilter, number>>;
  onChange: (filter: WallFilter) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-1 text-caption" data-wall-filters="">
      <Group
        label={copy.role}
        choices={ROLES.map((role) => ({ value: role, label: roleName(role) }))}
        value={filter.role}
        onChange={(role) => onChange({ ...filter, role })}
      />
      <Group
        label={copy.cells}
        choices={CELLS.map((cells) => ({ value: cells, label: measureName(cells) }))}
        value={filter.cells}
        onChange={(cells) => onChange({ ...filter, cells })}
      />
      <Group
        label={copy.status}
        choices={STATUSES.filter((status) => status === "all" || status === filter.status || counts[status] > 0).map(
          (status) => ({ value: status, label: STATUS_WORD[status], count: counts[status] }),
        )}
        value={filter.status}
        onChange={(status) => onChange({ ...filter, status })}
      />
    </div>
  );
}

/** The Rolle group alone, for «Vis i plenum» (Story 14.6): the same text buttons, no Celler or
 * Status. */
export function RoleFilter({ role, onChange }: { role: WallFilter["role"]; onChange: (role: WallFilter["role"]) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-1 text-caption" data-wall-filters="">
      <Group
        label={copy.role}
        choices={ROLES.map((value) => ({ value, label: roleName(value) }))}
        value={role}
        onChange={onChange}
      />
    </div>
  );
}

function Group<T extends string>({
  label,
  choices,
  value,
  onChange,
}: {
  label: string;
  choices: readonly Choice<T>[];
  value: T;
  onChange: (value: T) => void;
}) {
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} className="flex flex-wrap items-center gap-x-3">
      <span id={id} className="text-ink-secondary">
        {label}
      </span>
      {choices.map((choice) => {
        const pressed = choice.value === value;
        return (
          <button
            key={choice.value}
            type="button"
            aria-pressed={pressed}
            onClick={() => onChange(choice.value)}
            className={cn(
              "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center justify-center gap-1 text-ink tabular-nums lining-nums hover:underline",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
              pressed && "font-semibold underline underline-offset-4",
            )}
            data-filter={choice.value}
          >
            {choice.label}
            {choice.count !== undefined ? <span className="font-normal text-ink-secondary">{choice.count}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
