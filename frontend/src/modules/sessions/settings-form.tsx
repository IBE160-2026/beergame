"use client";

import { Fragment, type ReactNode, useEffect, useId, useRef, useState } from "react";

import { SegmentedChoice } from "@/components/segmented-choice";
import { SelectField } from "@/components/select-field";
import { TextAreaField } from "@/components/text-area-field";
import { Switch } from "@/components/switch";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import { type ClassSession, useDemandSeries } from "./api";
import { cappedRoles, roleName, type SettingRow, settingRows } from "./sessions";
import {
  type CapacityDraft,
  capacityProblem,
  type InfoVisibilityDraft,
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
 * allowed range, and its warnings as text. Under them «Ventetid før KI tar over» (Story 5.7) in
 * whole hours. Choices take effect only with «Lagre Klasseøkt».
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
  inactivity,
  inactivityError,
  onInactivityChange,
  onInactivityLeave,
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
  /** «Ventetid før KI tar over» as typed (Story 5.7): not a Game setting, so the web checks it
   * on leaving the field and on save, and the api holds the same floor. */
  inactivity: string;
  inactivityError: string | undefined;
  onInactivityChange: (text: string) => void;
  onInactivityLeave: () => void;
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
        {draft.capacity ? (
          <CapacityFields
            roles={item.game_settings.roles}
            capacity={draft.capacity}
            problem={capacityProblem(problems)}
            notes={warnings.capacity}
            onChange={(capacity) => onChange({ ...draft, capacity })}
            onLeave={onLeave}
          />
        ) : null}
        {draft.infoVisibility ? (
          <InfoVisibilityFields
            views={draft.infoVisibility}
            problem={problems.info_visibility}
            onChange={(infoVisibility) => onChange({ ...draft, infoVisibility })}
            onLeave={onLeave}
          />
        ) : null}
        <TextField
          id="setting-inactivity_limit_hours"
          label={nb.terms.inactivityLimit}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          className="mt-6 border-t border-hairline pt-4"
          inputClassName="lg:max-w-40"
          value={inactivity}
          hint={copy.edit.inactivityHint}
          error={inactivityError}
          errorAlert
          onChange={(event) => onInactivityChange(event.target.value)}
          onBlur={onInactivityLeave}
        />
        {(otherErrors(problems)[""] ?? []).map((text, index) => (
          <p key={`other-${index}`} className="mt-2 text-body-phone text-restordre">
            {text}
          </p>
        ))}
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

/** Whether the api's key belongs to the capacity («capacity», «capacity.retailer»). */
function isCapacityKey(name: string): boolean {
  return name === "capacity" || name.startsWith("capacity.");
}

/** The api's errors on settings with no field here, under the list. The Demand pattern's own stand
 * under its fields; one on a field the chosen pattern does not show cannot come from this draft. */
function otherErrors(problems: Readonly<Record<string, SettingProblem>>): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const [name, problem] of Object.entries(problems)) {
    if (EDITABLE_NAMES.includes(name) || isDemandKey(name) || isCapacityKey(name) || name === "info_visibility")
      continue;
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
 * each api error under its field with the allowed range. The web app holds no demand rule. The
 * Replay scenario (Story 10.2) shows it without the seed (`seed`), under its own ids (`idPrefix`),
 * with its own labels and a field after the change Week (`extra`), and warnings under «Mønster». */
export function DemandFields({
  demand,
  problems,
  onChange,
  onLeave,
  idPrefix = "setting",
  seed = true,
  labels = {},
  extra = {},
  notes,
}: {
  demand: DemandDraft;
  problems: Readonly<Record<string, SettingProblem>>;
  onChange: (demand: DemandDraft) => void;
  onLeave: () => void;
  idPrefix?: string;
  seed?: boolean;
  labels?: Partial<Record<DemandFieldName, string>>;
  extra?: Partial<Record<DemandFieldName, ReactNode>>;
  notes?: readonly string[];
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
          id={`${idPrefix}-demand-kind`}
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
          if (name === "seed" && !seed) return null;
          const problem = problems[demandProblemKey(name)];
          const field = { ...DEMAND_LABELS[name], label: labels[name] ?? DEMAND_LABELS[name].label };
          if (name === "values") {
            // 36–52 numbers do not fit one line (GitHub issue 102).
            return (
              <TextAreaField
                key={name}
                id={`${idPrefix}-demand-${name}`}
                label={field.label}
                rows={4}
                autoComplete="off"
                spellCheck={false}
                className="lg:col-span-2"
                value={demand[name]}
                hint={field.hint}
                error={problem ? problemText(problem) : undefined}
                onChange={(event) => onChange({ ...demand, [name]: event.target.value })}
                onBlur={onLeave}
              />
            );
          }
          return (
            <Fragment key={name}>
              <TextField
                id={`${idPrefix}-demand-${name}`}
                label={field.label}
                type="text"
                inputMode="numeric"
                autoComplete="off"
                className={name === "seed" ? "lg:col-span-2" : undefined}
                value={demand[name]}
                hint={field.hint}
                error={problem ? problemText(problem) : undefined}
                onChange={(event) => onChange({ ...demand, [name]: event.target.value })}
                onBlur={onLeave}
              />
              {extra[name]}
            </Fragment>
          );
        })}
      </div>
      {(notes ?? []).map((text) => (
        <p key={text} className="mt-2 text-body-phone text-ink">
          {text}
        </p>
      ))}
    </section>
  );
}

const c = copy.edit.capacity;

/** A shipping capacity (Story 5.15, cut list, FR-12): a Bryter, off by default; on, «Gjelder» as
 * Valgknapper (every Role or one), the Role for one, and the units per Week as a Tekstfelt with the
 * api's error and warnings under it, then the help line. Rendered only while `FEATURE_CAPACITY` is
 * on. The web app holds no range: the api judges the value as the field is left. */
function CapacityFields({
  roles,
  capacity,
  problem,
  notes,
  onChange,
  onLeave,
}: {
  roles: readonly CapacityDraft["role"][];
  capacity: CapacityDraft;
  problem: SettingProblem | undefined;
  notes: readonly string[] | undefined;
  onChange: (capacity: CapacityDraft) => void;
  onLeave: () => void;
}) {
  const titleId = useId();
  const helpId = useId();
  const scopeName = useId();
  // A change of scope, Role or switch is judged at once, as leaving a field is: after the render
  // that holds it, so the check sends the new draft.
  const pending = useRef(false);
  // Any change of the capacity replaces a stored map the switch cannot show (`kept`). With no units
  // typed yet there is nothing to judge, so no error shows before the Lecturer types.
  const change = (next: CapacityDraft) => onChange({ ...next, kept: undefined });
  const choose = (next: CapacityDraft) => {
    change(next);
    pending.current = next.units.trim() !== "";
  };
  useEffect(() => {
    if (!pending.current) return;
    pending.current = false;
    onLeave();
  });
  return (
    <section aria-labelledby={titleId} className="mt-6 border-t border-hairline pt-4">
      <h3 id={titleId} className="text-label text-ink">
        {c.legend}
      </h3>
      <Switch
        id="setting-capacity"
        className="mt-2"
        checked={capacity.on}
        labelledBy={titleId}
        describedBy={capacity.on ? helpId : undefined}
        onChange={(on) => choose({ ...capacity, on })}
      >
        {capacity.on ? c.on : c.off}
      </Switch>
      {capacity.on ? (
        <>
          <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <SegmentedChoice
              name={scopeName}
              legend={c.scope}
              className="lg:col-span-2"
              options={[
                { value: "all", label: c.all },
                { value: "one", label: c.one },
              ]}
              value={capacity.scope}
              onChange={(scope) => choose({ ...capacity, scope })}
            />
            {capacity.scope === "one" ? (
              <SelectField
                id="setting-capacity-role"
                label={c.role}
                value={capacity.role}
                onChange={(event) => choose({ ...capacity, role: event.target.value as CapacityDraft["role"] })}
              >
                {/* Fabrikk first, the one Seat order everywhere (GitHub issue 115). */}
                {[...roles].reverse().map((role) => (
                  <option key={role} value={role}>
                    {roleName(role)}
                  </option>
                ))}
              </SelectField>
            ) : null}
            <TextField
              id="setting-capacity-units"
              label={c.units}
              type="text"
              inputMode="numeric"
              autoComplete="off"
              value={capacity.units}
              hint={c.unitsHint}
              error={problem ? problemText(problem) : undefined}
              notes={notes}
              onChange={(event) => change({ ...capacity, units: event.target.value })}
              onBlur={onLeave}
            />
          </div>
          <p id={helpId} className="mt-3 text-body-phone text-ink-secondary">
            {c.help}
          </p>
        </>
      ) : problem ? (
        <p className="mt-2 text-body-phone text-restordre">{problemText(problem)}</p>
      ) : null}
    </section>
  );
}

const iv = copy.edit.infoVisibility;

/** Information visibility (Story 5.16, cut list, FR-83, UX-DR12): under the heading «Synlige naboer»
 * two Bryter, off by default, for the view of the Seat directly upstream and of the Seat directly
 * downstream, each naming the numbers it shows; then the help line with the scope. Rendered only
 * while `FEATURE_INFO_VISIBILITY` is on. A switch is judged by the api at once, as leaving a field. */
function InfoVisibilityFields({
  views,
  problem,
  onChange,
  onLeave,
}: {
  views: InfoVisibilityDraft;
  problem: SettingProblem | undefined;
  onChange: (views: InfoVisibilityDraft) => void;
  onLeave: () => void;
}) {
  const titleId = useId();
  const upId = useId();
  const downId = useId();
  const helpId = useId();
  // Judged after the render that holds the new draft, so the check sends it.
  const pending = useRef(false);
  useEffect(() => {
    if (!pending.current) return;
    pending.current = false;
    onLeave();
  });
  const choose = (next: InfoVisibilityDraft) => {
    onChange(next);
    pending.current = true;
  };
  const sides = [
    { side: "upstream", id: upId, label: iv.upstream, on: iv.upstreamOn },
    { side: "downstream", id: downId, label: iv.downstream, on: iv.downstreamOn },
  ] as const;
  return (
    <section aria-labelledby={titleId} className="mt-6 border-t border-hairline pt-4">
      <h3 id={titleId} className="text-label text-ink">
        {iv.legend}
      </h3>
      <div className="mt-2 grid grid-cols-1 gap-x-4 gap-y-2 lg:grid-cols-2">
        {sides.map(({ side, id, label, on }) => (
          <div key={side}>
            <p id={id} className="text-label text-ink">
              {label}
            </p>
            <Switch
              id={`setting-info-visibility-${side}`}
              checked={views[side]}
              labelledBy={`${titleId} ${id}`}
              describedBy={helpId}
              onChange={(checked) => choose({ ...views, [side]: checked })}
            >
              {views[side] ? on : iv.off}
            </Switch>
          </div>
        ))}
      </div>
      <p id={helpId} className="mt-3 text-body-phone text-ink-secondary">
        {iv.help}
      </p>
      {problem ? (
        <p className="mt-2 text-body-phone text-restordre">
          {problem.code === "feature_disabled" ? iv.disabled : problemText(problem)}
        </p>
      ) : null}
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

/** The saved settings as a list; a warning stands as a further description under its setting.
 * The api's errors on settings with no field show in the open block (`otherErrors`). */
function ReadOnlyRows({ item, warnings }: { item: ClassSession; warnings: Readonly<Record<string, string[]>> }) {
  const rows = settingRows(
    item.game_settings,
    item.inactivity_limit_hours,
    item.capacity_enabled,
    item.info_visibility_enabled,
  );
  const capped = item.capacity_enabled && cappedRoles(item.game_settings).length > 0;
  // A capacity is set (Story 5.15): what a capped Seat means, and that Students are told, under
  // its own row rather than under the list.
  const help: Record<string, string[]> = capped ? { capacity: [copy.edit.capacity.help] } : {};
  return <RowList rows={rows} warnings={warnings} errors={{}} help={help} />;
}

function RowList({
  rows,
  warnings,
  errors,
  help = {},
}: {
  rows: readonly SettingRow[];
  warnings: Readonly<Record<string, string[]>>;
  errors: Readonly<Record<string, string[]>>;
  help?: Readonly<Record<string, string[]>>;
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
          {(help[row.key] ?? []).map((text, index) => (
            <dd key={`help-${index}`} className="mt-1 basis-full text-body-phone text-ink-secondary">
              {text}
            </dd>
          ))}
        </div>
      ))}
    </dl>
  );
}
