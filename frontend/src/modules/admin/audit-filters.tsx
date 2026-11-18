"use client";

import { SelectField } from "@/components/select-field";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { type AuditFilters, useAuditActors } from "./api";
import { rangeError } from "./audit";

const copy = nb.admin.audit;

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
