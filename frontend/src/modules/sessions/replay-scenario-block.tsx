"use client";

import { Fragment, useId, useRef, useState } from "react";

import { SegmentedChoice } from "@/components/segmented-choice";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";

import { checkReplayScenario, type ClassSession, type ReplayScenarioBody } from "./api";
import {
  hiddenLine,
  ownHiddenLine,
  ownRows,
  type ReplayDraft,
  replayDraftOf,
  type ReplayTemplate,
  replayTemplateBody,
  replayWarningsByField,
  scenarioRows,
} from "./replay-scenario";
import { EDITABLE, problemsOf, problemText, type SettingProblem } from "./settings";
import { DemandFields, InfoVisibilityFields } from "./settings-form";

const copy = nb.sessions.replay;

type Choice = ClassSession["replay_scenario"];

/**
 * The Replay scenario as the Lecturer sets it on the Klasseøkt (Story 10.2): the choice, the own
 * scenario as typed, and what the api last said of it. Sent with «Lagre Klasseøkt» (`body`); a
 * refusal puts each reason under its field (`refused`).
 */
export function useReplayScenario(item: ClassSession) {
  const [choice, setChoiceState] = useState<Choice>(item.replay_scenario);
  const [draft, setDraft] = useState<ReplayDraft>(() => replayDraftOf(item));
  const [problems, setProblems] = useState<Record<string, SettingProblem>>({});
  const [warnings, setWarnings] = useState(() => replayWarningsByField(item.replay_warnings));
  const checked = useRef("");
  const checks = useRef(0);

  // Leaving a field: the api judges the whole draft (AD-1). A later answer wins.
  const check = (next: ReplayDraft = draft) => {
    const body = replayTemplateBody(next);
    const key = JSON.stringify(body);
    if (key === checked.current) return;
    checked.current = key;
    const run = ++checks.current;
    checkReplayScenario(item.id, body).then(
      (result) => {
        if (run !== checks.current) return;
        setProblems(result.errors);
        setWarnings(replayWarningsByField(result.warnings));
      },
      () => {
        // A check that fails says nothing; the save judges the draft again.
        if (run === checks.current) checked.current = "";
      },
    );
  };

  return {
    choice,
    draft,
    problems,
    warnings,
    setDraft,
    check,
    /** Valgknapper: an own scenario opens on what was typed so far, at first the stored own
     * template or the Game settings, and is judged at once so its warnings show before anything
     * is typed. */
    setChoice(next: Choice) {
      setChoiceState(next);
      if (next !== "own") return;
      checked.current = "";
      check();
    },
    /** What «Lagre Klasseøkt» sends. */
    body(): ReplayScenarioBody {
      return choice === "own"
        ? { replay_scenario: "own", replay_template: replayTemplateBody(draft) }
        : { replay_scenario: "default" };
    },
    /** A save refused the scenario: its reasons stand under their fields. */
    refused(error: unknown) {
      if (error instanceof ApiRequestError && error.code === "invalid_replay_scenario") {
        checks.current += 1;
        setProblems(problemsOf(error.fields));
      }
    },
    /** The saved Class session: the form starts again from what is stored. */
    saved(result: ClassSession) {
      checks.current += 1;
      checked.current = "";
      setChoiceState(result.replay_scenario);
      setDraft(replayDraftOf(result));
      setProblems({});
      setWarnings(replayWarningsByField(result.replay_warnings));
    },
  };
}

export type ReplayScenarioState = ReturnType<typeof useReplayScenario>;

/**
 * The Klasseøkt's «Replay-scenario» (Stories 10.1 and 10.2, FR-49, FR-72, UX-DR12, UX-DR48). Before
 * the Start date its owner chooses with Valgknapper between «Standard», described in words from
 * the template the api derives from the Game settings, and «Eget scenario»: every Game setting
 * prefilled from the Class session's, the seed aside, with Weeks and the change Week as one value
 * or a range drawn per Student. The api's errors stand under their fields with the range, and its
 * warnings of changes that probably make the Replay easier as text; neither leaves the screen
 * before «Lagre Klasseøkt». Locked, or for an Assistant, the scenario in force stands as a list.
 */
export function ReplayScenarioBlock({
  item,
  editable,
  state,
}: {
  item: ClassSession;
  editable: boolean;
  state: ReplayScenarioState;
}) {
  const titleId = useId();
  const helpId = useId();
  const choice = editable ? state.choice : item.replay_scenario;
  return (
    <section aria-labelledby={titleId} className="mt-12 max-w-3xl border-t border-hairline pt-6" data-replay-scenario="">
      <h2 id={titleId} className="text-label text-ink">
        {copy.title}
      </h2>
      {editable ? (
        <>
          <SegmentedChoice
            name="replay-scenario"
            className="mt-2 lg:[&_label]:flex-none"
            legend={copy.choice}
            options={[
              { value: "default", label: copy.standard },
              { value: "own", label: copy.own },
            ]}
            value={state.choice}
            onChange={state.setChoice}
            describedBy={helpId}
          />
          <p id={helpId} className="mt-2 text-body-phone text-ink-secondary">
            {copy.choiceHelp}
          </p>
        </>
      ) : (
        <p className="mt-2 text-body-phone text-ink lg:text-body">{choice === "own" ? copy.own : copy.standard}</p>
      )}
      {choice === "own" && editable ? (
        <OwnScenarioForm state={state} />
      ) : choice === "own" ? (
        <OwnScenarioRows
          template={item.replay_template}
          warnings={replayWarningsByField(item.replay_warnings)}
          infoVisibilityEnabled={item.info_visibility_enabled}
        />
      ) : (
        <DefaultRows template={editable && item.replay_scenario === "own" ? item.replay_default : item.replay_template} />
      )}
    </section>
  );
}

function DefaultRows({ template }: { template: ReplayTemplate }) {
  return (
    <>
      <dl className="mt-4 max-w-2xl">
        {scenarioRows(template).map((row) => (
          <div
            key={row.label}
            className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-hairline py-2"
          >
            <dt className="text-body-phone text-ink lg:text-body">{row.label}</dt>
            <dd className="text-right text-body-phone font-semibold text-ink tabular-nums lg:text-body">{row.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 max-w-2xl text-body-phone text-ink-secondary">{hiddenLine(template)}</p>
    </>
  );
}

function OwnScenarioRows({
  template,
  warnings,
  infoVisibilityEnabled,
}: {
  template: ReplayTemplate;
  warnings: Record<string, string[]>;
  infoVisibilityEnabled: boolean;
}) {
  return (
    <>
      <dl className="mt-4 max-w-2xl">
        {ownRows(template, infoVisibilityEnabled).map((row) => (
          <div
            key={row.key}
            className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-hairline py-2"
          >
            <dt className="text-body-phone text-ink lg:text-body">{row.label}</dt>
            <dd className="text-right text-body-phone font-semibold text-ink tabular-nums lg:text-body">{row.value}</dd>
            {(warnings[row.key] ?? []).map((text) => (
              <dd key={text} className="mt-1 basis-full text-body-phone text-ink">
                {text}
              </dd>
            ))}
          </div>
        ))}
      </dl>
      <p className="mt-3 max-w-2xl text-body-phone text-ink-secondary">{ownHiddenLine(template)}</p>
    </>
  );
}

const FIELD_KEYS: readonly string[] = [...EDITABLE.map((field) => field.name), "demand"];

/** The own scenario's fields: the Game settings' Tekstfelt under Replay ids, «Antall uker» as
 * «minst» and «høyst», then the Demand pattern without the seed and the change Week as «tidligst»
 * and «senest». */
function OwnScenarioForm({ state }: { state: ReplayScenarioState }) {
  const { draft, problems, warnings, setDraft, check } = state;
  const others = Object.entries(problems).filter(
    ([name]) =>
      !FIELD_KEYS.includes(name) &&
      !name.startsWith("demand.") &&
      name !== "demand_seed" &&
      !(name === "info_visibility" && draft.infoVisibility),
  );
  const error = (name: string) => (problems[name] ? problemText(problems[name]) : undefined);
  return (
    <div className="mt-4">
      <p className="text-body-phone text-ink-secondary">{copy.ownLead}</p>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {EDITABLE.map((field) => (
          <Fragment key={field.name}>
            <TextField
              id={`replay-${field.name}`}
              label={field.name === "weeks" ? copy.weeksFrom : field.label}
              type="text"
              inputMode={field.kind === "cost" ? "decimal" : "numeric"}
              autoComplete="off"
              value={draft[field.name]}
              hint={"hint" in field ? field.hint : undefined}
              error={error(field.name)}
              notes={warnings[field.name]}
              onChange={(event) => setDraft({ ...draft, [field.name]: event.target.value })}
              onBlur={() => check()}
            />
            {field.name === "weeks" ? (
              <TextField
                id="replay-weeks-to"
                label={copy.weeksTo}
                type="text"
                inputMode="numeric"
                autoComplete="off"
                value={draft.weeksTo}
                hint={copy.toHint}
                onChange={(event) => setDraft({ ...draft, weeksTo: event.target.value })}
                onBlur={() => check()}
              />
            ) : null}
          </Fragment>
        ))}
      </div>
      <DemandFields
        demand={draft.demand}
        problems={problems}
        onChange={(demand) => setDraft({ ...draft, demand })}
        onLeave={() => check()}
        idPrefix="replay"
        seed={false}
        labels={{ change_week: copy.changeWeekFrom }}
        notes={warnings.demand}
        extra={{
          change_week: (
            <TextField
              id="replay-demand-change_week-to"
              label={copy.changeWeekTo}
              type="text"
              inputMode="numeric"
              autoComplete="off"
              value={draft.changeWeekTo}
              hint={copy.toHint}
              onChange={(event) => setDraft({ ...draft, changeWeekTo: event.target.value })}
              onBlur={() => check()}
            />
          ),
        }}
      />
      {draft.infoVisibility ? (
        <InfoVisibilityFields
          views={draft.infoVisibility}
          problem={problems.info_visibility}
          onChange={(infoVisibility) => setDraft({ ...draft, infoVisibility })}
          onLeave={() => check()}
          idPrefix="replay-info-visibility"
          help={copy.infoVisibilityHelp}
          notes={warnings.info_visibility}
        />
      ) : null}
      {others.map(([name, problem]) => (
        <p key={name} className="mt-2 text-body-phone text-restordre">
          {problemText(problem)}
        </p>
      ))}
    </div>
  );
}
