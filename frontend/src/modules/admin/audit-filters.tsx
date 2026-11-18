"use client";

import type { SelectHTMLAttributes } from "react";

import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { type AuditFilters, useAuditActors } from "./api";
import { rangeError } from "./audit";

const copy = nb.admin.audit;

/** A labelled native select, styled as the Tekstfelt (DESIGN.md → Components → Controls). */
function SelectField({
  id,
  label,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { id: string; label: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-field-gap">
      <label htmlFor={id} className="text-label text-ink">
        {label}
      </label>
      <select
        {...props}
        id={id}
        className="min-h-control-height-phone w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink"
      >
        {children}
      </select>
    </div>
  );
}

/**
 * The filters of «Revisjonslogg» (Story 3.12): «Utført av», «Handling», «Fra og med» and
 * «Til og med». Each change applies at once; there is no submit button. A range that ends before
 * it starts shows the reason under «Til og med», and the list keeps the last valid filters.
 */
export function AuditFiltersForm({ value, onChange }: { value: AuditFilters; onChange: (next: AuditFilters) => void }) {
  const actors = useAuditActors();
  const reversed = rangeError(value.since, value.until);
  const set = (key: keyof AuditFilters) => (event: { target: { value: string } }) =>
    onChange({ ...value, [key]: event.target.value });

  return (
    <form
      role="search"
      aria-labelledby="audit-filters-title"
      onSubmit={(event) => event.preventDefault()}
      className="@container"
    >
      <h2 id="audit-filters-title" className="sr-only">
        {copy.filters.title}
      </h2>
      <div className="grid grid-cols-1 gap-4 @min-[36em]:grid-cols-2 @min-[60em]:grid-cols-4">
        <SelectField id="audit-actor" label={copy.filters.actor} value={value.actor} onChange={set("actor")}>
          <option value="">{copy.filters.all}</option>
          {(actors.data?.items ?? []).map((actor) => (
            <option key={actor.id ?? "system"} value={actor.id ?? "system"}>
              {actor.id === null ? copy.system : (actor.name ?? copy.unknown)}
            </option>
          ))}
        </SelectField>
        <SelectField id="audit-action" label={copy.filters.action} value={value.action} onChange={set("action")}>
          <option value="">{copy.filters.all}</option>
          {Object.entries(copy.actions).map(([action, label]) => (
            <option key={action} value={action}>
              {label}
            </option>
          ))}
        </SelectField>
        <TextField
          id="audit-since"
          type="date"
          label={copy.filters.since}
          value={value.since}
          onChange={set("since")}
        />
        <TextField
          id="audit-until"
          type="date"
          label={copy.filters.until}
          value={value.until}
          error={reversed}
          onChange={set("until")}
        />
      </div>
    </form>
  );
}
