"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { useClass } from "@/modules/classes/api";
import { classPath, classSessionPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import {
  checkClassSessionSettings,
  type ClassSession,
  classSessionKey,
  classSessionsKey,
  lecturerHomeKey,
  saveClassSession,
  useClassSession,
} from "./api";
import { ChainDiagram } from "./chain-diagram";
import { DateFields } from "./date-fields";
import { DateLine } from "./date-line";
import { type DateInputs, dateErrors, datesBody, inputsOf } from "./dates";
import { calibratedText, draftOf, problemsOf, type SettingProblem, settingsBody, warningsBySetting } from "./settings";
import { SettingsBlock } from "./settings-form";

const copy = nb.sessions;

/** The shape of a Class session id (a UUID). */
const SESSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Klasseøkt (Story 5.1, FR-11, UX-DR48): a new Class session as the API filled it in with the
 * Classic defaults, «Kjeden ved start» drawn from the values it returned, and «Lagre Klasseøkt»,
 * which saves it as it stands. The Game settings open in place for changes (Story 5.3). An
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
  const [saved, setSaved] = useState(false);
  // The Game settings as typed while the block is open (Story 5.3), and what the api last said of
  // them: errors by setting and warnings in words.
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(() => draftOf(settings));
  const [problems, setProblems] = useState<Record<string, SettingProblem>>({});
  const [warnings, setWarnings] = useState(() => warningsBySetting(item.settings_warnings));
  const checked = useRef("");
  const checks = useRef(0);
  const action = useAction({
    mutationFn: async () => {
      try {
        return await saveClassSession(
          item.id,
          item.ai_mode,
          datesBody(inputs),
          editing && item.can_manage && !item.locked ? settingsBody(draft) : undefined,
        );
      } catch (error) {
        if (error instanceof ApiRequestError && error.code === "invalid_settings") {
          checks.current += 1;
          setProblems(problemsOf(error.fields));
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
    },
    onSuccess: (result) => {
      queryClient.setQueryData(classSessionKey(item.id), result);
      void queryClient.invalidateQueries({ queryKey: classSessionsKey(item.class_id), exact: true });
      void queryClient.invalidateQueries({ queryKey: lecturerHomeKey, exact: true });
      setInputs(inputsOf(result));
      setTestTouched(result.test_deadline != null);
      // The saved values stand in the list; the block opens again for a next change.
      checks.current += 1;
      setProblems({});
      setEditing(false);
      setSaved(true);
    },
  });
  // Leaving a changed field: the api judges the whole draft (AD-1). A later answer wins.
  const checkDraft = () => {
    const body = settingsBody(draft);
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
    const stored = draftOf(item.game_settings);
    setDraft(stored);
    checked.current = JSON.stringify(settingsBody(stored));
    setProblems({});
    setWarnings(warningsBySetting(item.settings_warnings));
    setEditing(true);
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
  return (
    <>
      {item.is_classic ? <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.defaults}</p> : null}
      {readOnlyLine ? (
        <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{readOnlyLine}</p>
      ) : null}
      <div className="mt-8 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
        <section aria-labelledby="settings-title" className="min-w-0">
          <h2 id="settings-title" className="text-headline text-ink">
            {item.is_classic ? copy.settingsTitle : copy.settingsTitleChanged}
          </h2>
          {item.is_classic ? null : (
            <p className="mt-2 text-body-phone text-ink-secondary">{calibratedText(item.calibrated_settings)}</p>
          )}
          {item.locked && item.can_manage ? <p className="mt-2 text-body-phone text-ink">{copy.edit.locked}</p> : null}
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
          />
          <p className="mt-3 text-body-phone text-ink-secondary">{copy.delaySources}</p>
          <div className="mt-8">
            <ChainDiagram settings={settings} />
          </div>
        </section>
        <section aria-labelledby={datesTitle} className="min-w-0">
          <h2 id={datesTitle} className="text-headline text-ink">
            {copy.dates.title}
          </h2>
          <DateLine dates={item} titleId={datesTitle} />
          <DateFields
            inputs={inputs}
            testTouched={testTouched}
            onChange={(next, touched) => {
              setInputs(next);
              setTestTouched(touched);
            }}
            errors={dateErrors(action.error, inputs)}
            passed={item.passed_dates}
            readOnly={!item.can_manage}
          />
          {item.play_time_warning ? (
            <p className="mt-3 text-body-phone text-ink lg:text-body">{copy.dates.playTimeShort(settings.weeks)}</p>
          ) : null}
        </section>
      </div>
      <Choices item={item} />
      {item.can_manage ? (
        <SaveRow
          pending={action.isPending}
          errorMessage={action.errorMessage}
          saved={saved && !action.isError}
          onSave={() => {
            if (action.isPending) return;
            setSaved(false);
            action.mutate();
          }}
        />
      ) : null}
    </>
  );
}

/** KI-modus, Debrief-modus and Obligatorisk as they stand (Stories 5.5 and 5.7 make them choices). */
function Choices({ item }: { item: ClassSession }) {
  const c = copy.choices;
  const blocks = [
    { title: c.aiMode, value: item.ai_mode === "llm" ? c.llm : c.ruleBased },
    { title: c.debriefMode, value: item.debrief_mode === "group" ? c.group : c.personal },
    { title: c.obligatory, value: item.obligatory ? c.obligatoryYes : c.obligatoryNo },
  ];
  return (
    <div className="mt-12 grid grid-cols-1 gap-6 border-t border-hairline pt-6 lg:grid-cols-3">
      {blocks.map((block) => (
        <section key={block.title}>
          <h2 className="text-label text-ink">{block.title}</h2>
          <p className="mt-2 text-body-phone text-ink lg:text-body">{block.value}</p>
          {block.title === c.aiMode && item.llm_unavailable ? (
            <p className="mt-2 max-w-md text-body-phone text-ink-secondary">{c.llmUnavailable}</p>
          ) : null}
        </section>
      ))}
    </div>
  );
}

/** «Lagre Klasseøkt», the screen's primary button. A failure keeps focus and values. */
function SaveRow({
  pending,
  errorMessage,
  saved,
  onSave,
}: {
  pending: boolean;
  errorMessage: string | undefined;
  saved: boolean;
  onSave: () => void;
}) {
  return (
    <div className="mt-10 flex flex-col items-start gap-3 lg:items-end">
      <div className="flex flex-col-reverse items-start gap-3 lg:flex-row lg:items-center lg:gap-6">
        <p id="save-hint" className="text-body-phone text-ink-secondary">
          {copy.saveHint}
        </p>
        <Button
          variant="primary"
          unavailable={pending}
          aria-describedby="save-hint"
          onClick={onSave}
        >
          {pending ? copy.saving : copy.save}
        </Button>
      </div>
      <ActionError message={errorMessage} />
      <p role="status" className="text-body-phone text-ink">
        {saved ? copy.saved : ""}
      </p>
    </div>
  );
}
