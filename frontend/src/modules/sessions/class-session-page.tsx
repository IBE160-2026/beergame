"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SegmentedChoice } from "@/components/segmented-choice";
import { Switch } from "@/components/switch";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";
import { cn } from "@/lib/utils";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { useClass } from "@/modules/classes/api";
import { QuizExclusionsBlock } from "@/modules/debrief/quiz-exclusions";
import { classOverviewPath, classPath, classSessionPath, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import {
  allocationKey,
  checkClassSessionSettings,
  type ClassSession,
  classSessionKey,
  classSessionsKey,
  lecturerHomeKey,
  saveClassSession,
  useClassSession,
} from "./api";
import { AllocationBlock } from "./allocation-panel";
import { ChainDiagram } from "./chain-diagram";
import {
  type ChoicesDraft,
  choicesBody,
  choicesOf,
  descriptionBlocks,
  effectLine,
  levelLabel,
  methodBody,
  withAiMode,
} from "./choices";
import { DateFields } from "./date-fields";
import { DateLine } from "./date-line";
import {
  DATE_NAMES,
  type DateInputs,
  type DateName,
  dateErrors,
  datesBody,
  datesEditable,
  frozenDates,
  inputsOf,
  osloDateText,
} from "./dates";
import { LabHours } from "./lab-hours-panel";
import { inactivityProblem, shareProblem, valueErrorsOf } from "./obligatory";
import { ReplayScenarioBlock, useReplayScenario } from "./replay-scenario-block";
import { copyLines } from "./rerun";
import {
  calibratedText,
  DISABLED_PROBLEM,
  disabledSettings,
  draftOf,
  hasClassicDelays,
  problemsOf, type SettingProblem, settingsBody, warningsBySetting } from "./settings";
import { SettingsBlock } from "./settings-form";
import { TestGameBlock } from "./test-game-panel";

const copy = nb.sessions;

/** The shape of a Class session id (a UUID). */
const SESSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Klasseøkt (Story 5.1, FR-11, UX-DR48): a new Class session as the API filled it in with the
 * Classic defaults, «Kjeden ved start» drawn from the values it returned, and «Lagre Klasseøkt»,
 * which saves it as it stands. The Game settings open in place for changes (Story 5.3); «Fordeling»
 * previews a random allocation in place (Story 5.8); KI-modus,
 * Innsatsnivå and Debrief-modus are Valgknapper that take effect on save (Story 5.5). An
 * Assistant lecturer reads it with no action. Anything the User may not reach shows the
 * permission-denied page (FR-5).
 */
export function ClassSessionPage({ sessionId }: { sessionId: string }) {
  const named = SESSION_ID.test(sessionId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <ClassSessionView sessionId={sessionId} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function ClassSessionView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useClassSession(sessionId);
  const { phase, retry } = usePageState(found, classSessionKey(sessionId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const item = found.data;
  const crumbs = item
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: item.class_name, href: classPath(item.class_id) },
        { label: copy.crumb, href: classSessionPath(item.id) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={item ? copy.title(item.class_name) : undefined}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={item ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {item ? <ClassSessionBody item={item} /> : null}
    </PageShell>
  );
}

function ClassSessionBody({ item }: { item: ClassSession }) {
  const settings = item.game_settings;
  const queryClient = useQueryClient();
  const datesTitle = useId();
  // The date fields as typed; they take effect only when «Lagre Klasseøkt» saves them.
  const [inputs, setInputs] = useState<DateInputs>(() => inputsOf(item));
  const [testTouched, setTestTouched] = useState(item.test_deadline != null);
  // A date field the browser holds half-typed reads as "" (GitHub issue 100): the save stops with
  // a reason under it rather than clear the date.
  const dateFields = useRef<Partial<Record<DateName, HTMLInputElement | null>>>({});
  const [halfTyped, setHalfTyped] = useState<readonly DateName[]>([]);
  const [saved, setSaved] = useState(false);
  // A Lab hour form is open (Story 5.6): its save is the primary button meanwhile.
  const [labFormOpen, setLabFormOpen] = useState(false);
  // «Bekreft fordeling» shows in the open allocation panel (Story 5.9): it is the primary button then.
  const [confirmShown, setConfirmShown] = useState(false);
  // KI-modus, Innsatsnivå and Debrief-modus as chosen; sent with «Lagre Klasseøkt» (Story 5.5).
  const [choices, setChoices] = useState<ChoicesDraft>(() => choicesOf(item));
  const choosing = item.can_manage && !item.locked;
  // The allocation method as chosen (Story 5.17); a change to Student choice is sent on save.
  const [method, setMethod] = useState(item.allocation_method);
  // «Andel uker som kreves» and «Ventetid før KI tar over» (Story 5.7): their reasons show once the
  // field is left or «Lagre Klasseøkt» pressed.
  const [shareChecked, setShareChecked] = useState(false);
  const [inactivity, setInactivity] = useState(() => String(item.inactivity_limit_hours));
  const [inactivityChecked, setInactivityChecked] = useState(false);
  // The Game settings as typed while the block is open (Story 5.3), and what the api last said of
  // them: errors by setting and warnings in words.
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => draftOf(settings, item.capacity_enabled, item.info_visibility_enabled));
  const [problems, setProblems] = useState<Record<string, SettingProblem>>({});
  const [warnings, setWarnings] = useState(() => warningsBySetting(item.settings_warnings));
  const checked = useRef("");
  const checks = useRef(0);
  const settingsOpen = editing && item.can_manage && !item.locked;
  // The Replay scenario as chosen (Story 10.2): sent with «Lagre Klasseøkt» while it can change.
  const replay = useReplayScenario(item);
  const action = useAction({
    mutationFn: async () => {
      try {
        return await saveClassSession(
          item.id,
          // Once locked the choices stand as stored; the api refuses any change.
          choosing ? { ...choicesBody(choices), ...methodBody(method, item) } : { ai_mode: item.ai_mode },
          datesBody(inputs),
          settingsOpen ? settingsBody(draft, item.game_settings.roles) : undefined,
          settingsOpen ? Number(inactivity.trim()) : undefined,
          choosing ? replay.body() : undefined,
        );
      } catch (error) {
        replay.refused(error);
        if (error instanceof ApiRequestError && error.code === "invalid_settings") {
          checks.current += 1;
          setProblems(problemsOf(error.fields));
        }
        // A setting switched off here (GitHub issue 114): the reason stands at its field only.
        const disabled = disabledSettings(error);
        if (disabled.length > 0) {
          checks.current += 1;
          setProblems(Object.fromEntries(disabled.map((name) => [name, DISABLED_PROBLEM])));
        }
        throw error;
      }
    },
    messages: {
      llm_unavailable: copy.llmRefused,
      invalid_dates: copy.dates.refused,
      deadline_passed: copy.dates.refused,
      session_locked: copy.dates.locked,
      invalid_settings: copy.edit.refused,
      invalid_replay_scenario: copy.replay.refused,
      feature_disabled: copy.edit.featureDisabled,
      invalid_effort_level: copy.choices.effortRefused,
      invalid_session_values: copy.choices.valuesRefused,
      allocation_confirmed: copy.allocation.methodConfirmed,
    },
    onSuccess: (result) => {
      queryClient.setQueryData(classSessionKey(item.id), result);
      void queryClient.invalidateQueries({ queryKey: classSessionsKey(item.class_id), exact: true });
      void queryClient.invalidateQueries({ queryKey: lecturerHomeKey, exact: true });
      // Student choice saved (Story 5.17): the block now lists the empty Class games.
      if (result.allocation_method !== item.allocation_method) {
        void queryClient.invalidateQueries({ queryKey: allocationKey(item.id), exact: true });
      }
      setInputs(inputsOf(result));
      setChoices(choicesOf(result));
      setMethod(result.allocation_method);
      setTestTouched(result.test_deadline != null);
      setShareChecked(false);
      setInactivity(String(result.inactivity_limit_hours));
      setInactivityChecked(false);
      replay.saved(result);
      // The saved values stand in the list; the block opens again for a next change.
      checks.current += 1;
      setProblems({});
      setEditing(false);
      setSaved(true);
    },
  });
  // Leaving a changed field: the api judges the whole draft (AD-1). A later answer wins.
  const checkDraft = () => {
    const body = settingsBody(draft, item.game_settings.roles);
    const key = JSON.stringify(body);
    if (key === checked.current) return;
    checked.current = key;
    const run = ++checks.current;
    checkClassSessionSettings(item.id, body).then(
      (result) => {
        if (run !== checks.current) return;
        setProblems(result.errors);
        setWarnings(warningsBySetting(result.warnings));
      },
      () => {
        // A check that fails says nothing; the save judges the draft again.
        if (run === checks.current) checked.current = "";
      },
    );
  };
  const openSettings = () => {
    const stored = draftOf(item.game_settings, item.capacity_enabled, item.info_visibility_enabled);
    setDraft(stored);
    checked.current = JSON.stringify(settingsBody(stored, item.game_settings.roles));
    setProblems({});
    setWarnings(warningsBySetting(item.settings_warnings));
    setInactivity(String(item.inactivity_limit_hours));
    setInactivityChecked(false);
    setEditing(true);
  };
  // The web's own checks of the share and the Ventetid, else what the api said of them.
  const refusedValues = valueErrorsOf(action.error);
  const shareError =
    (choosing && choices.obligatory && shareChecked ? shareProblem(choices.requiredShare) : undefined) ??
    refusedValues.share;
  const inactivityError =
    (settingsOpen && inactivityChecked ? inactivityProblem(inactivity) : undefined) ?? refusedValues.inactivity;
  /** Whether the drafts the web checks itself may be sent; shows each reason otherwise. */
  const valuesReady = () => {
    const shareWrong = choosing && choices.obligatory && shareProblem(choices.requiredShare) !== undefined;
    const inactivityWrong = settingsOpen && inactivityProblem(inactivity) !== undefined;
    // Only a field on screen is marked checked, so a share field that opens later is not judged
    // before it is left.
    setShareChecked(choosing && choices.obligatory);
    setInactivityChecked(settingsOpen);
    return !shareWrong && !inactivityWrong;
  };
  const cancelSettings = () => {
    checks.current += 1;
    setEditing(false);
  };
  // Why nothing can be changed: the Class is archived (Story 4.10), or the User is its Assistent.
  const klass = useClass(item.class_id).data;
  const readOnlyLine = item.can_manage
    ? null
    : klass?.archived
      ? nb.classes.archive.notice
      : klass?.staff_role === "assistant"
        ? copy.assistantLead
        : null;
  // Locked (Story 5.11, GitHub issue 103): what is frozen stands as text, and the only save is the
  // deadlines', while one can still move.
  const deadlinesOpen = datesEditable(item);
  const copied = copyLines(item);
  const saveShown = item.can_manage && (!item.locked || deadlinesOpen);
  const saveRow = (
    <SaveRow
      locked={item.locked}
      secondary={labFormOpen || confirmShown}
      pending={action.isPending}
      // The reason of a switched-off setting stands at its field; the save line only says it was
      // not saved (GitHub issue 114).
      errorMessage={disabledSettings(action.error).length > 0 ? copy.edit.notSaved : action.errorMessage}
      saved={saved && !action.isError}
      onSave={() => {
        if (action.isPending) return;
        setSaved(false);
        const half = DATE_NAMES.filter((name) => dateFields.current[name]?.validity.badInput);
        setHalfTyped(half);
        const ready = valuesReady();
        if (half.length > 0 || !ready) {
          // Nothing is sent; the reasons stand under their fields.
          action.reset();
          if (half.length > 0) dateFields.current[half[0]]?.focus();
          return;
        }
        action.mutate();
      }}
    />
  );
  return (
    <>
      {item.locked ? (
        <div className="mt-2 max-w-3xl">
          <p className="text-body-phone text-ink lg:text-body">
            {item.locked_at ? copy.lock.lockedAt(osloDateText(item.locked_at)) : copy.lock.pending}
          </p>
          {/* The sweep refused the lock for a missing provider key (GitHub issue 109): the owner
              learns it here too, not only from the mail. */}
          {!item.locked_at && item.lock_refused && item.can_manage ? (
            <p className="mt-1 text-body-phone font-semibold text-ink lg:text-body">{copy.lock.refused}</p>
          ) : null}
          {item.can_manage ? (
            <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">
              {deadlinesOpen ? copy.lock.open : copy.lock.labHoursOpen}
            </p>
          ) : null}
        </div>
      ) : copied.length > 0 ? (
        // A copy names its source until it is first saved (Story 5.18).
        <div className="mt-2 max-w-3xl">
          {copied.map((line) => (
            <p key={line} className="text-body-phone text-ink lg:text-body">
              {line}
            </p>
          ))}
        </div>
      ) : item.is_classic ? (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.defaults}</p>
      ) : null}
      {readOnlyLine ? (
        <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{readOnlyLine}</p>
      ) : null}
      {/* Every Class game's status, whom it waits for and its cost (Story 7.1). */}
      <PageLink href={classOverviewPath(item.id)}>{nb.overview.open}</PageLink>
      <div className="mt-8 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
        <section aria-labelledby="settings-title" className="min-w-0">
          <h2 id="settings-title" className="text-headline text-ink">
            {item.is_classic ? copy.settingsTitle : copy.settingsTitleChanged}
          </h2>
          {item.is_classic ? null : (
            <p className="mt-2 text-body-phone text-ink-secondary">{calibratedText(item.calibrated_settings)}</p>
          )}
          <SettingsBlock
            item={item}
            editable={item.can_manage && !item.locked}
            open={editing && item.can_manage && !item.locked}
            draft={draft}
            problems={problems}
            warnings={editing ? warnings : warningsBySetting(item.settings_warnings)}
            onOpen={openSettings}
            onCancel={cancelSettings}
            onChange={setDraft}
            onLeave={checkDraft}
            inactivity={inactivity}
            inactivityError={inactivityError}
            onInactivityChange={setInactivity}
            onInactivityLeave={() => setInactivityChecked(true)}
          />
          {/* It speaks of Classic's delays and says they can be changed: only with those, and not
              once locked (Story 5.11, GitHub issue 101). */}
          {item.locked || !hasClassicDelays(settings, item.calibrated_settings) ? null : (
            <p className="mt-3 text-body-phone text-ink-secondary">{copy.delaySources}</p>
          )}
          <div className="mt-8">
            <ChainDiagram settings={settings} capacityEnabled={item.capacity_enabled} />
          </div>
        </section>
        <section aria-labelledby={datesTitle} className="min-w-0">
          <h2 id={datesTitle} className="text-headline text-ink">
            {copy.dates.title}
          </h2>
          <DateLine dates={item} labHours={item.lab_hours} titleId={datesTitle} />
          <LabHours item={item} onOpenChange={setLabFormOpen} />
          <DateFields
            inputs={inputs}
            values={item}
            testTouched={testTouched}
            onChange={(next, touched) => {
              setInputs(next);
              setTestTouched(touched);
              setHalfTyped((prev) => (prev.length > 0 ? prev.filter((name) => next[name] === inputs[name]) : prev));
            }}
            fieldRefs={dateFields}
            errors={{
              ...dateErrors(action.error, inputs),
              ...Object.fromEntries(halfTyped.map((name) => [name, copy.dates.errors.incomplete])),
            }}
            passed={item.passed_dates}
            frozen={frozenDates(item)}
            readOnly={!item.can_manage}
          />
          {item.play_time_warning ? (
            <p className="mt-3 text-body-phone text-ink lg:text-body">{copy.dates.playTimeShort(settings.weeks)}</p>
          ) : null}
          {/* Locked, «Lagre frister» saves only these fields, so it sits under them. */}
          {saveShown && item.locked ? saveRow : null}
          <AllocationBlock item={item} method={method} onMethodChange={setMethod} onConfirmShown={setConfirmShown} />
        </section>
      </div>
      <Choices
        item={item}
        draft={choices}
        editable={choosing}
        onChange={setChoices}
        shareError={shareError}
        onShareLeave={() => setShareChecked(true)}
      />
      {/* Stories 10.1 and 10.2 (FR-49): the Replay scenario, frozen at the Start date like the
          choices above. */}
      <ReplayScenarioBlock item={item} editable={choosing} state={replay} />
      {saveShown && !item.locked ? saveRow : null}
      {/* Story 9.10: its own save, since exclusions stay open after the lock until the Test deadline. */}
      <QuizExclusionsBlock classSessionId={item.id} />
      <TestGameBlock item={item} />
    </>
  );
}

/** On a wide screen each segment is as wide as its label, as in mockup 03; on a phone the
 * segments share the row. */
const CONTENT_SIZED = "lg:[&_label]:flex-none";
/** Two long options stacked on a phone: each a whole segment of its own, with a gap (Story 9.2). */
const STACKED_ON_PHONE = "max-sm:[&_label]:ml-0 max-sm:[&_label]:basis-full max-sm:[&_label]:rounded-sm";

/**
 * KI-modus, Debrief-modus with «Når Debriefen åpner» (Story 9.2, FR-42) and the Bryter «KI-tekst i
 * Debriefen» (Story 9.14, FR-15, FR-44), and Obligatorisk (Story
 * 5.5, FR-15, FR-16, FR-78, UX-DR48, UX-DR49). The
 * first two are Valgknapper while the session is unlocked and the User may change it; «Innsatsnivå»
 * shows only with LLM players, with the levels the api offers. Locked, or for an Assistant, the
 * values stand as text. Obligatorisk is a Bryter with «Andel uker som kreves» under it while on
 * (Story 5.7, FR-17, UX-DR12, UX-DR78): the switch's label is the whole confirmation, with no
 * dialog, and like the Valgknapper it takes effect on «Lagre Klasseøkt».
 */
function Choices({
  item,
  draft,
  editable,
  onChange,
  shareError,
  onShareLeave,
}: {
  item: ClassSession;
  draft: ChoicesDraft;
  editable: boolean;
  onChange: (next: ChoicesDraft) => void;
  shareError: string | undefined;
  onShareLeave: () => void;
}) {
  const c = copy.choices;
  const ids = useId();
  const scopeId = `${ids}-scope`;
  const reasonId = `${ids}-reason`;
  const debriefHelpId = `${ids}-debrief`;
  const releaseHelpId = `${ids}-release`;
  const shown = editable ? draft : choicesOf(item);
  const llm = shown.aiMode === "llm";
  const levels = item.effort_levels;
  const inForce = levels.find((level) => level.name === shown.effortLevel);
  return (
    <div className="mt-12 grid grid-cols-1 gap-x-16 gap-y-10 border-t border-hairline pt-6 lg:grid-cols-3">
      <section aria-labelledby={editable ? undefined : `${ids}-ai`} className="min-w-0">
        {editable ? (
          <SegmentedChoice
            name="ai-mode"
            className={CONTENT_SIZED}
            legend={c.aiMode}
            options={[
              {
                value: "llm",
                label: c.llm,
                unavailable: item.llm_unavailable != null,
                describedBy: item.llm_unavailable != null ? reasonId : undefined,
              },
              { value: "rule_based", label: c.ruleBased },
            ]}
            value={draft.aiMode}
            onChange={(aiMode) => onChange(withAiMode(draft, aiMode, item))}
            describedBy={scopeId}
          />
        ) : (
          <>
            <h2 id={`${ids}-ai`} className="text-label text-ink">
              {c.aiMode}
            </h2>
            <p className="mt-2 text-body-phone text-ink lg:text-body">{llm ? c.llm : c.ruleBased}</p>
          </>
        )}
        <p id={scopeId} className="mt-2 text-body-phone text-ink-secondary">
          {c.aiScope}
        </p>
        {item.llm_unavailable ? (
          <p id={reasonId} className="mt-2 max-w-md text-body-phone text-ink-secondary">
            {c.llmUnavailable}
          </p>
        ) : null}
        {item.provider_unavailable && llm && !item.locked ? (
          <p className="mt-2 max-w-md text-body-phone text-ink">{c.providerUnavailable}</p>
        ) : null}
        {llm && editable && levels.length > 0 ? (
          <EffortLevels
            levels={levels}
            value={draft.effortLevel ?? levels[0].name}
            onChange={(effortLevel) => onChange({ ...draft, effortLevel })}
          />
        ) : llm && shown.effortLevel ? (
          // Read-only, or nothing offered here: the level in force as text, under its label as the
          // other locked values stand (GitHub issue 109).
          <div role="group" aria-labelledby={`${ids}-effort`} className="mt-6">
            <h3 id={`${ids}-effort`} className="text-label text-ink">
              {c.effortLevel}
            </h3>
            <p className="mt-2 text-body-phone text-ink lg:text-body">
              {inForce ? levelLabel(inForce) : shown.effortLevel}
            </p>
          </div>
        ) : null}
        <AiDescriptions item={item} />
      </section>
      <section aria-labelledby={editable ? undefined : `${ids}-debrief-title`} className="min-w-0">
        {editable ? (
          <SegmentedChoice
            name="debrief-mode"
            className={CONTENT_SIZED}
            legend={c.debriefMode}
            options={[
              { value: "group", label: c.group },
              { value: "personal", label: c.personal },
            ]}
            value={draft.debriefMode}
            onChange={(debriefMode) => onChange({ ...draft, debriefMode })}
            describedBy={debriefHelpId}
          />
        ) : (
          <>
            <h2 id={`${ids}-debrief-title`} className="text-label text-ink">
              {c.debriefMode}
            </h2>
            <p className="mt-2 text-body-phone text-ink lg:text-body">
              {shown.debriefMode === "group" ? c.group : c.personal}
            </p>
          </>
        )}
        <p id={debriefHelpId} className="mt-2 text-body-phone text-ink-secondary">
          {shown.debriefMode === "group" ? c.groupHelp : c.personalHelp}
        </p>
        {/* Story 9.2 (FR-42, UX-DR12): when the Debriefs open, frozen at the Start date. */}
        <div className="mt-6">
          {editable ? (
            <SegmentedChoice
              name="debrief-release"
              className={cn(CONTENT_SIZED, STACKED_ON_PHONE)}
              legend={c.debriefRelease}
              options={[
                { value: "open", label: c.releaseOpen },
                { value: "hold", label: c.releaseHold },
              ]}
              value={draft.debriefRelease}
              onChange={(debriefRelease) => onChange({ ...draft, debriefRelease })}
              describedBy={releaseHelpId}
            />
          ) : (
            <div role="group" aria-labelledby={`${ids}-release-title`}>
              <h3 id={`${ids}-release-title`} className="text-label text-ink">
                {c.debriefRelease}
              </h3>
              <p className="mt-2 text-body-phone text-ink lg:text-body">
                {shown.debriefRelease === "hold" ? c.releaseHold : c.releaseOpen}
              </p>
            </div>
          )}
          <p id={releaseHelpId} className="mt-2 text-body-phone text-ink-secondary">
            {shown.debriefRelease === "hold" ? c.releaseHoldHelp : c.releaseOpenHelp}
          </p>
        </div>
        {/* Story 9.14 (FR-15, FR-44): the Debrief's AI text, a Bryter frozen at the Start date. */}
        <div role="group" aria-labelledby={`${ids}-ai-text`} className="mt-6" data-debrief-ai-text="">
          <h3 id={`${ids}-ai-text`} className="text-label text-ink">
            {c.debriefAiText}
          </h3>
          {editable ? (
            <Switch
              id={`${ids}-ai-text-switch`}
              className="mt-1"
              checked={draft.debriefAiText}
              onChange={(debriefAiText) => onChange({ ...draft, debriefAiText })}
              labelledBy={`${ids}-ai-text`}
              describedBy={`${ids}-ai-text-help`}
            >
              {draft.debriefAiText ? c.debriefAiTextOn : c.debriefAiTextOff}
            </Switch>
          ) : (
            <p className="mt-2 text-body-phone text-ink lg:text-body">
              {shown.debriefAiText ? c.debriefAiTextOn : c.debriefAiTextOff}
            </p>
          )}
          <p id={`${ids}-ai-text-help`} className="mt-2 text-body-phone text-ink-secondary">
            {shown.debriefAiText ? c.debriefAiTextOnHelp : c.debriefAiTextOffHelp}
          </p>
        </div>
      </section>
      <section aria-labelledby={`${ids}-obligatory`} className="min-w-0">
        <h2 id={`${ids}-obligatory`} className="text-label text-ink">
          {c.obligatory}
        </h2>
        {editable ? (
          <Switch
            id={`${ids}-obligatory-switch`}
            className="mt-1"
            checked={draft.obligatory}
            onChange={(obligatory) => onChange({ ...draft, obligatory })}
            labelledBy={`${ids}-obligatory`}
            describedBy={draft.obligatory ? `${ids}-obligatory-help` : undefined}
          >
            {draft.obligatory ? c.obligatoryYes : c.obligatoryNo}
          </Switch>
        ) : (
          <p className="mt-2 text-body-phone text-ink lg:text-body">
            {shown.obligatory ? c.obligatoryYes : c.obligatoryNo}
          </p>
        )}
        {shown.obligatory ? (
          <p id={`${ids}-obligatory-help`} className="mt-2 text-body-phone text-ink-secondary">
            {c.obligatoryHelp}
          </p>
        ) : null}
        {shown.obligatory && editable ? (
          <TextField
            id={`${ids}-share`}
            className="mt-4"
            inputClassName="max-w-32"
            label={c.share}
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={draft.requiredShare}
            hint={c.shareHint}
            error={shareError}
            errorAlert
            onChange={(event) => onChange({ ...draft, requiredShare: event.target.value })}
            onBlur={onShareLeave}
          />
        ) : shown.obligatory ? (
          <p className="mt-4 text-body-phone text-ink lg:text-body">{c.shareValue(item.required_share_percent)}</p>
        ) : null}
      </section>
    </div>
  );
}

/** «Innsatsnivå»: the offered levels as Valgknapper, each with its one effect line (FR-78). */
function EffortLevels({
  levels,
  value,
  onChange,
}: {
  levels: ClassSession["effort_levels"];
  value: string;
  onChange: (name: string) => void;
}) {
  const ids = useId();
  return (
    <div className="mt-6">
      <SegmentedChoice
        name="effort-level"
        className={CONTENT_SIZED}
        legend={copy.choices.effortLevel}
        options={levels.map((level, i) => ({
          value: level.name,
          label: levelLabel(level),
          describedBy: `${ids}-${i}`,
        }))}
        value={value}
        onChange={onChange}
      />
      <ul className="mt-2 flex flex-col gap-1">
        {levels.map((level, i) => (
          <li key={level.name} className="text-body-phone text-ink-secondary">
            <span className="font-semibold text-ink">{levelLabel(level)}:</span>{" "}
            <span id={`${ids}-${i}`}>{effectLine(level)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** How each AI player type decides, as `players.service.describe` words it (FR-33). */
function AiDescriptions({ item }: { item: ClassSession }) {
  const c = copy.choices;
  const types = [
    { key: "llm", title: c.aboutLlm, text: item.ai_descriptions.llm },
    { key: "rule_based", title: c.aboutRuleBased, text: item.ai_descriptions.rule_based },
  ];
  return (
    <div className="mt-4 flex flex-col gap-1">
      {types.map((type) => (
        <details key={type.key}>
          <summary className={`${LINK_BUTTON} list-none [&::-webkit-details-marker]:hidden`}>{type.title}</summary>
          <div className="mt-2 mb-4 flex max-w-prose flex-col gap-3 text-body-phone text-ink">
            {descriptionBlocks(type.text).map((block, i) =>
              block.kind === "paragraph" ? (
                <p key={i}>{block.text}</p>
              ) : (
                <ul key={i} className="list-disc pl-5">
                  {block.items.map((entry, j) => (
                    <li key={j}>{entry}</li>
                  ))}
                </ul>
              ),
            )}
          </div>
        </details>
      ))}
    </div>
  );
}

/** «Lagre Klasseøkt», the screen's primary button, secondary while an in-place form with its own
 * primary is open (Story 5.6) or «Bekreft fordeling» shows (Story 5.9). Once locked it is «Lagre
 * frister», which saves only the deadlines that can still move (Story 5.11). A failure keeps focus
 * and values. */
function SaveRow({
  locked,
  secondary,
  pending,
  errorMessage,
  saved,
  onSave,
}: {
  locked: boolean;
  secondary: boolean;
  pending: boolean;
  errorMessage: string | undefined;
  saved: boolean;
  onSave: () => void;
}) {
  return (
    <div className="mt-10 flex flex-col items-start gap-3 lg:items-end">
      <div className="flex flex-col-reverse items-start gap-3 lg:flex-row lg:items-center lg:gap-6">
        <p id="save-hint" className="text-body-phone text-ink-secondary">
          {locked ? copy.lock.saveHint : copy.saveHint}
        </p>
        <Button
          variant={secondary ? "secondary" : "primary"}
          unavailable={pending}
          aria-describedby="save-hint"
          onClick={onSave}
        >
          {pending ? copy.saving : locked ? copy.lock.save : copy.save}
        </Button>
      </div>
      <ActionError message={errorMessage} />
      <p role="status" className="text-body-phone text-ink">
        {saved ? (locked ? copy.lock.saved : copy.saved) : ""}
      </p>
    </div>
  );
}
