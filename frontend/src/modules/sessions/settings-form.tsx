"use client";

import { useEffect, useRef } from "react";

import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import type { ClassSession } from "./api";
import { type SettingRow, settingRows } from "./sessions";
import { EDITABLE, problemText, type SettingProblem, type SettingsDraft } from "./settings";

const copy = nb.sessions;

/**
 * The settings block of the Klasseøkt (Stories 5.1 and 5.3, FR-12, UX-DR48). Closed, it is the
 * list of the saved settings, each warning on its own line under its setting. An owner of a
 * session that has not started opens it in place with «Endre spillinnstillinger»: the settings
 * become Tekstfelt fields, labels above, focus on the first. Leaving a field asks the api to judge
 * the draft (`onLeave`); its errors show under the field with the allowed range, and its warnings
 * as text. Choices take effect only with «Lagre Klasseøkt».
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
        <ReadOnlyRows
          item={item}
          only={["demand", "inactivity_limit_hours"]}
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
      {editable ? (
        <button ref={opener} type="button" className={`${LINK_BUTTON} mt-3`} onClick={onOpen}>
          {copy.edit.open}
        </button>
      ) : null}
    </>
  );
}

const EDITABLE_NAMES: readonly string[] = EDITABLE.map((field) => field.name);

/** The api's errors on settings with no field here, by the row they stand under: a Demand-pattern
 * rule (`demand.change_week` when the Weeks end before the change) under «Etterspørsel», anything
 * else under the list. */
function otherErrors(problems: Readonly<Record<string, SettingProblem>>): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const [name, problem] of Object.entries(problems)) {
    if (EDITABLE_NAMES.includes(name)) continue;
    const row = name === "demand" || name.startsWith("demand.") ? "demand" : "";
    (result[row] ??= []).push(problemText(problem));
  }
  return result;
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
