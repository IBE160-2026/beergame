"use client";

import { useEffect, useId, useRef, useState } from "react";

import { SelectField } from "@/components/select-field";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import { type ClassSession, useDemandSeries } from "./api";
import { type SettingRow, settingRows } from "./sessions";
import {
  DEMAND_FIELDS,
  DEMAND_KINDS,
  type DemandDraft,
  type DemandFieldName,
  demandProblemKey,
  EDITABLE,
  problemText,
  type SettingProblem,
  type SettingsDraft,
  withKind,
} from "./settings";

const copy = nb.sessions;

/**
 * The settings block of the Klasseøkt (Stories 5.1, 5.3 and 5.4, FR-12, FR-13, UX-DR48). Closed,
 * it is the list of the saved settings, each warning on its own line under its setting, and
 * «Vis etterspørselen uke for uke», which shows the saved series as a table. An owner of a
 * session that has not started opens it in place with «Endre spillinnstillinger»: the settings
 * become Tekstfelt fields, labels above, focus on the first, and under them the Demand pattern:
 * «Mønster» and the chosen pattern's fields, with the seed for a pattern that draws. Leaving a
 * field asks the api to judge the draft (`onLeave`); its errors show under the field with the
 * allowed range, and its warnings as text. Choices take effect only with «Lagre Klasseøkt».
 */
export function SettingsBlock({
  item,
  editable,
  open,
  draft,
  problems,
  warnings,
  onOpen,
  onCancel,
  onChange,
  onLeave,
}: {
  item: ClassSession;
  editable: boolean;
  open: boolean;
  draft: SettingsDraft;
  problems: Readonly<Record<string, SettingProblem>>;
  warnings: Readonly<Record<string, string[]>>;
  onOpen: () => void;
  onCancel: () => void;
  onChange: (draft: SettingsDraft) => void;
  onLeave: () => void;
}) {
  const first = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(open);
  const cancelled = useRef(false);
  useEffect(() => {
    // Focus follows the block: into the first field on open, back to the opener on cancel. After
    // a save it stays on «Lagre Klasseøkt».
    if (open && !wasOpen.current) first.current?.focus();
    if (!open && wasOpen.current && cancelled.current) opener.current?.focus();
    cancelled.current = false;
    wasOpen.current = open;
  }, [open]);

  if (open) {
    return (
      <div className="mt-4">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {EDITABLE.map((field, index) => {
            const problem = problems[field.name];
            return (
              <TextField
                key={field.name}
                ref={index === 0 ? first : undefined}
                id={`setting-${field.name}`}
                label={field.label}
                type="text"
                inputMode={field.kind === "cost" ? "decimal" : "numeric"}
                autoComplete="off"
                value={draft[field.name]}
                hint={"hint" in field ? field.hint : undefined}
                error={problem ? problemText(problem) : undefined}
                notes={warnings[field.name]}
                onChange={(event) => onChange({ ...draft, [field.name]: event.target.value })}
                onBlur={onLeave}
              />
            );
          })}
        </div>
        <DemandFields
          demand={draft.demand}
          problems={problems}
          onChange={(demand) => onChange({ ...draft, demand })}
          onLeave={onLeave}
        />
        <ReadOnlyRows
          item={item}
          only={["inactivity_limit_hours"]}
          warnings={warnings}
          errors={otherErrors(problems)}
        />
        <button
          type="button"
          className={`${LINK_BUTTON} mt-3`}
          onClick={() => {
            cancelled.current = true;
            onCancel();
          }}
        >
          {copy.edit.cancel}
        </button>
      </div>
    );
  }
  return (
    <>
      <ReadOnlyRows item={item} warnings={warnings} />
      <DemandSeries item={item} />
      {editable ? (
        <button ref={opener} type="button" className={`${LINK_BUTTON} mt-3`} onClick={onOpen}>
          {copy.edit.open}
        </button>
      ) : null}
    </>
  );
}

const EDITABLE_NAMES: readonly string[] = EDITABLE.map((field) => field.name);

/** Whether the api's key belongs to the Demand pattern or its seed. */
function isDemandKey(name: string): boolean {
  return name === "demand" || name === "demand_seed" || name.startsWith("demand.");
}

/** The api's errors on settings with no field here, under the list. The Demand pattern's own stand
 * under its fields; one on a field the chosen pattern does not show cannot come from this draft. */
function otherErrors(problems: Readonly<Record<string, SettingProblem>>): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const [name, problem] of Object.entries(problems)) {
    if (EDITABLE_NAMES.includes(name) || isDemandKey(name)) continue;
    (result[""] ??= []).push(problemText(problem));
  }
  return result;
}

const d = copy.edit.demand;

const DEMAND_LABELS: Record<DemandFieldName, { label: string; hint?: string }> = {
  values: { label: d.values, hint: d.valuesHint },
  start: { label: d.start },
  new_level: { label: d.newLevel },
  change_week: { label: d.changeWeek },
  mean: { label: d.mean },
  spread: { label: d.spread, hint: d.spreadHint },
  seed: { label: d.seed, hint: d.seedHint },
};

/** The Demand pattern (Story 5.4, FR-13): «Mønster» and the chosen pattern's fields as Tekstfelt,
 * each api error under its field with the allowed range. The web app holds no demand rule. */
function DemandFields({
  demand,
  problems,
  onChange,
  onLeave,
}: {
  demand: DemandDraft;
  problems: Readonly<Record<string, SettingProblem>>;
  onChange: (demand: DemandDraft) => void;
  onLeave: () => void;
}) {
  const titleId = useId();
  const patternProblem = problems.demand;
  return (
    <section aria-labelledby={titleId} className="mt-6 border-t border-hairline pt-4">
      <h3 id={titleId} className="text-label text-ink">
        {d.legend}
      </h3>
      <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SelectField
          id="setting-demand-kind"
          label={d.pattern}
          value={demand.kind}
          error={patternProblem ? copy.edit.errors.pattern : undefined}
          onChange={(event) => onChange(withKind(demand, event.target.value as DemandDraft["kind"]))}
          onBlur={onLeave}
        >
          {DEMAND_KINDS.map((kind) => (
            <option key={kind} value={kind}>
              {d.kinds[kind]}
            </option>
          ))}
        </SelectField>
        {DEMAND_FIELDS[demand.kind].map((name) => {
          const problem = problems[demandProblemKey(name)];
          const field = DEMAND_LABELS[name];
          return (
            <TextField
              key={name}
              id={`setting-demand-${name}`}
              label={field.label}
              type="text"
              inputMode={name === "values" ? "text" : "numeric"}
              autoComplete="off"
              className={name === "values" || name === "seed" ? "lg:col-span-2" : undefined}
              value={demand[name]}
              hint={field.hint}
              error={problem ? problemText(problem) : undefined}
              onChange={(event) => onChange({ ...demand, [name]: event.target.value })}
              onBlur={onLeave}
            />
          );
        })}
      </div>
    </section>
  );
}

/** «Vis etterspørselen uke for uke» (Story 5.4, FR-13): the saved series as the api materialised
 * it, a table of Week and demand, for the Class's staff. */
function DemandSeries({ item }: { item: ClassSession }) {
  const s = copy.edit.series;
  const [shown, setShown] = useState(false);
  const panelId = useId();
  const found = useDemandSeries(item, shown);
  return (
    <div className="mt-3">
      <button
        type="button"
        className={LINK_BUTTON}
        aria-expanded={shown}
        aria-controls={panelId}
        onClick={() => setShown(!shown)}
      >
        {shown ? s.hide : s.show}
      </button>
      <div id={panelId} hidden={!shown} className="mt-3">
        {!shown ? null : found.data ? (
          <div
            role="region"
            aria-label={s.caption}
            tabIndex={0}
            className="max-h-80 max-w-xs overflow-y-auto rounded-sm border border-hairline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
          >
            <table className="w-full border-collapse text-body-phone tabular-nums">
              <caption className="sr-only">{s.caption}</caption>
              <thead className="sticky top-0 bg-paper">
                <tr className="border-b border-hairline">
                  <th scope="col" className="px-3 py-2 text-left text-label text-ink">
                    {s.week}
                  </th>
                  <th scope="col" className="px-3 py-2 text-right text-label text-ink">
                    {s.demand}
                  </th>
                </tr>
              </thead>
              <tbody>
                {found.data.demand.map((value, index) => (
                  <tr key={index} className="border-b border-hairline last:border-b-0">
                    <th scope="row" className="px-3 py-1 text-left font-normal text-ink">
                      {index + 1}
                    </th>
                    <td className="px-3 py-1 text-right font-semibold text-ink">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : found.isError ? (
          <p role="alert" className="text-body-phone text-restordre">
            {s.failed}
          </p>
        ) : (
          <p className="text-body-phone text-ink-secondary">{s.loading}</p>
        )}
      </div>
    </div>
  );
}

/** The saved settings as a list; a warning, or an error on a setting with no field, stands as a
 * further description under its setting. */
function ReadOnlyRows({
  item,
  only,
  warnings,
  errors = {},
}: {
  item: ClassSession;
  only?: readonly string[];
  warnings: Readonly<Record<string, string[]>>;
  errors?: Readonly<Record<string, string[]>>;
}) {
  const rows = settingRows(item.game_settings, item.inactivity_limit_hours).filter(
    (row) => !only || only.includes(row.key),
  );
  return (
    <>
      <RowList rows={rows} warnings={warnings} errors={errors} />
      {(errors[""] ?? []).map((text, index) => (
        <p key={`other-${index}`} className="mt-2 text-body-phone text-restordre">
          {text}
        </p>
      ))}
    </>
  );
}

function RowList({
  rows,
  warnings,
  errors,
}: {
  rows: readonly SettingRow[];
  warnings: Readonly<Record<string, string[]>>;
  errors: Readonly<Record<string, string[]>>;
}) {
  return (
    <dl className="mt-4">
      {rows.map((row) => (
        <div
          key={row.label}
          className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-hairline py-2"
        >
          <dt className="text-body-phone text-ink lg:text-body">{row.label}</dt>
          <dd className="text-right text-body-phone font-semibold text-ink tabular-nums lg:text-body">{row.value}</dd>
          {(errors[row.key] ?? []).map((text, index) => (
            <dd key={`error-${index}`} className="mt-1 basis-full text-body-phone text-restordre">
              {text}
            </dd>
          ))}
          {(warnings[row.key] ?? []).map((text, index) => (
            <dd key={`warning-${index}`} className="mt-1 basis-full text-body-phone text-ink">
              {text}
            </dd>
          ))}
        </div>
      ))}
    </dl>
  );
}
