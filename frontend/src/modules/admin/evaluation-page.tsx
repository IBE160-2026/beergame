"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_EVALUATION_PATH, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import {
  type EvaluationSession,
  evaluationSessionsKey,
  useEvaluationExports,
  useEvaluationSessions,
  useKeyState,
  useRecordAgreement,
  useReplaceKey,
  useRunExport,
} from "./api";
import { formatTime } from "./audit";
import {
  AGREEMENT_TEXT_MAX,
  type AgreementErrors,
  agreementErrors,
  EXPORT_SESSIONS_MAX,
  formatDay,
  keyError,
  outcomeText,
  runRefusal,
  sessionLabel,
  shortFingerprint,
  todayInOslo,
} from "./evaluation";
import { formatDate } from "./invitations";
import { Cell, type RowLine, RowMessage } from "./user-list";

const copy = nb.admin.evaluation;

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: copy.title, href: ADMIN_EVALUATION_PATH },
] as const;

const TABLE =
  "w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop";
const HEAD = "py-2 pr-6 align-bottom text-label font-semibold text-ink";

/**
 * «Pseudonymisert eksport» in the Admin-område (Story 15.4, FR-71, FR-77): the Class sessions with
 * their Institution agreements and deletion dates, the run with the key holder's key (the page's
 * one primary button downloads the ZIP), the key's fingerprint with its replacement, and every run
 * and refusal. Only an Admin sees it; anyone else gets the permission-denied page.
 */
export function EvaluationPage() {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={CRUMBS}>
          <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <Sessions />
        </PageShell>
      )}
    </GuardedPage>
  );
}

function Sessions() {
  const sessions = useEvaluationSessions();
  const pageState = usePageState(sessions, evaluationSessionsKey);
  const items = sessions.data?.items ?? [];
  return (
    <>
      <section aria-labelledby="sessions-title" className="mt-10 @container">
        <h2 id="sessions-title" className="text-headline text-ink">
          {copy.sessions.title}
        </h2>
        <p className="mt-2 mb-5 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.sessions.lead}</p>
        {pageState.phase === "loading" || pageState.phase === "slow" ? (
          <div>
            <Skeleton heading={false} rows={3} columns={4} />
            <LoadingNote visible={pageState.phase === "slow"} />
          </div>
        ) : null}
        {pageState.phase === "failed" ? (
          <div className="flex flex-col items-start gap-3">
            <p role="alert" className="text-body-phone text-restordre lg:text-body">
              {nb.system.pageError}
            </p>
            <Button onClick={pageState.retry}>{nb.system.retry}</Button>
          </div>
        ) : null}
        {pageState.phase === "ready" ? <SessionTable items={items} /> : null}
      </section>
      {pageState.phase === "ready" ? <RunForm items={items.filter((item) => item.agreement)} /> : null}
      <KeySection />
      <ExportList />
    </>
  );
}

function SessionTable({ items }: { items: EvaluationSession[] }) {
  const [editing, setEditing] = useState<string>();
  const [line, setLine] = useState<RowLine>();
  const [focusRow, setFocusRow] = useState<{ id: string; n: number }>();
  const columns = copy.sessions.columns;

  useEffect(() => {
    if (focusRow) document.getElementById(`agreement-${focusRow.id}`)?.focus();
  }, [focusRow]);

  if (items.length === 0) return <p className="text-body-phone text-ink lg:text-body">{copy.sessions.empty}</p>;

  function close(item: EvaluationSession, saved: boolean) {
    setEditing(undefined);
    if (saved)
      setLine({
        key: item.id,
        text: copy.agreementForm.saved(sessionLabel(item)),
        refused: false,
      });
    setFocusRow((prev) => ({ id: item.id, n: (prev?.n ?? 0) + 1 }));
  }

  return (
    <table className={TABLE}>
      <thead className="@max-[60em]:hidden">
        <tr className="border-b border-axis">
          <th scope="col" className={HEAD}>
            {columns.session}
          </th>
          <th scope="col" className={`${HEAD} w-[9em]`}>
            {columns.testDeadline}
          </th>
          <th scope="col" className={`${HEAD} w-[9em]`}>
            {columns.deletion}
          </th>
          <th scope="col" className={HEAD}>
            {columns.agreement}
          </th>
          <th scope="col" className={HEAD}>
            {columns.actions}
          </th>
        </tr>
      </thead>
      <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
        {items.map((item) => {
          const label = sessionLabel(item);
          return (
            <tr key={item.id} className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3">
              <Cell label={columns.session}>
                <span className="font-semibold [overflow-wrap:anywhere]">{label}</span>
                {item.institution_name ? (
                  <span className="block text-ink-secondary [overflow-wrap:anywhere]">{item.institution_name}</span>
                ) : null}
              </Cell>
              <Cell label={columns.testDeadline}>
                {item.test_deadline ? formatDate(item.test_deadline) : copy.sessions.noDate}
              </Cell>
              <Cell label={columns.deletion}>
                {item.deletion_date ? formatDay(item.deletion_date) : copy.sessions.noDate}
              </Cell>
              <Cell label={columns.agreement}>
                {item.agreement ? (
                  <span className="[overflow-wrap:anywhere]">
                    {copy.sessions.agreement(item.agreement.agreed_by, formatDay(item.agreement.agreed_on))}
                    <span className="block text-ink-secondary">
                      {copy.sessions.controller(item.agreement.controller)}
                    </span>
                  </span>
                ) : (
                  copy.sessions.noAgreement
                )}
              </Cell>
              <td className="py-3 @max-[60em]:block @max-[60em]:pt-2 @max-[60em]:pb-0 @min-[60em]:w-[22em]">
                {editing === item.id ? (
                  <AgreementForm item={item} onDone={(saved) => close(item, saved)} />
                ) : (
                  <Button
                    id={`agreement-${item.id}`}
                    className="[overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                    onClick={() => {
                      setLine(undefined);
                      setEditing(item.id);
                    }}
                  >
                    {item.agreement ? copy.sessions.change(label) : copy.sessions.record(label)}
                  </Button>
                )}
                <RowMessage line={line?.key === item.id && editing !== item.id ? line : undefined} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** The inline agreement form of one row: who agreed, the day, the controller, «Lagre avtalen». */
function AgreementForm({ item, onDone }: { item: EvaluationSession; onDone: (saved: boolean) => void }) {
  const record = useRecordAgreement();
  const form = copy.agreementForm;
  const [values, setValues] = useState({
    agreedBy: item.agreement?.agreed_by ?? "",
    agreedOn: item.agreement?.agreed_on ?? "",
    controller: item.agreement?.controller ?? "",
  });
  const [errors, setErrors] = useState<AgreementErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const firstRef = useRef<HTMLInputElement>(null);
  const id = (name: string) => `${name}-${item.id}`;

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  function change(next: Partial<typeof values>) {
    const merged = { ...values, ...next };
    setValues(merged);
    if (submitted) setErrors(agreementErrors(merged, todayInOslo()));
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (record.isPending) return;
    const found = agreementErrors(values, todayInOslo());
    setErrors(found);
    setSubmitted(true);
    record.reset();
    if (Object.keys(found).length > 0) {
      const first = (["agreedBy", "agreedOn", "controller"] as const).find((name) => found[name]);
      if (first) document.getElementById(id(first))?.focus();
      return;
    }
    record.mutate(
      {
        id: item.id,
        body: {
          agreed_by: values.agreedBy.trim(),
          agreed_on: values.agreedOn,
          controller: values.controller.trim(),
        },
      },
      { onSuccess: () => onDone(true) },
    );
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
      <TextField
        ref={firstRef}
        id={id("agreedBy")}
        label={form.agreedBy}
        hint={form.agreedByHint}
        autoComplete="off"
        maxLength={AGREEMENT_TEXT_MAX}
        value={values.agreedBy}
        error={errors.agreedBy}
        onChange={(event) => change({ agreedBy: event.target.value })}
      />
      <TextField
        id={id("agreedOn")}
        type="date"
        label={form.agreedOn}
        max={todayInOslo()}
        value={values.agreedOn}
        error={errors.agreedOn}
        onChange={(event) => change({ agreedOn: event.target.value })}
      />
      <TextField
        id={id("controller")}
        label={form.controller}
        autoComplete="off"
        maxLength={AGREEMENT_TEXT_MAX}
        value={values.controller}
        error={errors.controller}
        onChange={(event) => change({ controller: event.target.value })}
      />
      <ActionError message={record.isError ? form.failed : undefined} />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button type="submit" unavailable={record.isPending} className="@max-[60em]:w-full">
          {form.save}
        </Button>
        <button
          type="button"
          aria-disabled={record.isPending ? true : undefined}
          onClick={() => {
            if (!record.isPending) onDone(false);
          }}
          className="inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink"
        >
          {form.cancel}
        </button>
      </div>
    </form>
  );
}

/** «Kjør eksport»: the Class sessions with an agreement as checkboxes, the key, and the page's one
 * primary button. The key field is emptied after every run, allowed or refused. */
function RunForm({ items }: { items: EvaluationSession[] }) {
  const run = useRunExport();
  const [chosen, setChosen] = useState<string[]>([]);
  const [choiceError, setChoiceError] = useState<string>();
  const [keyReason, setKeyReason] = useState<string>();
  const [done, setDone] = useState<string>();
  const keyRef = useRef<HTMLInputElement>(null);
  const doneRef = useRef<HTMLParagraphElement>(null);
  const form = copy.run;

  useEffect(() => {
    if (done) doneRef.current?.focus();
  }, [done]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (run.isPending) return;
    setDone(undefined);
    run.reset();
    const ids = chosen.filter((id) => items.some((item) => item.id === id));
    const choice = ids.length === 0 ? form.pickOne : ids.length > EXPORT_SESSIONS_MAX ? form.tooMany : undefined;
    const key = keyRef.current?.value ?? "";
    const reason = keyError(key);
    setChoiceError(choice);
    setKeyReason(reason);
    if (choice || reason) {
      if (reason) keyRef.current?.focus();
      return;
    }
    run.mutate(
      { ids, key: key.trim() },
      {
        onSuccess: ({ blob, name }) => {
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = name;
          document.body.append(link);
          link.click();
          link.remove();
          window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
          setDone(form.done(name));
        },
        onSettled: () => {
          if (keyRef.current) keyRef.current.value = "";
        },
      },
    );
  }

  return (
    <section aria-labelledby="run-title" className="mt-12">
      <h2 id="run-title" className="text-headline text-ink">
        {form.title}
      </h2>
      <p className="mt-2 mb-5 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{form.lead}</p>
      {items.length === 0 ? (
        <p className="text-body-phone text-ink lg:text-body">{form.none}</p>
      ) : (
        <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-xl flex-col gap-5">
          <fieldset aria-describedby={choiceError ? "run-sessions-error" : undefined} className="flex flex-col gap-1">
            <legend className="mb-2 text-label text-ink">{form.sessions}</legend>
            {items.map((item) => (
              <label
                key={item.id}
                className="group relative flex min-h-tap-target-min cursor-pointer items-center gap-3 rounded-sm pr-2 text-body-phone text-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink lg:text-body"
              >
                <input
                  type="checkbox"
                  className="absolute inset-0 m-0 size-full cursor-pointer opacity-0"
                  checked={chosen.includes(item.id)}
                  onChange={(event) => {
                    setChoiceError(undefined);
                    setChosen((prev) =>
                      event.target.checked ? [...prev, item.id] : prev.filter((id) => id !== item.id),
                    );
                  }}
                />
                <span
                  aria-hidden="true"
                  className="flex size-5 shrink-0 items-center justify-center rounded-sm border border-ink-muted bg-paper group-hover:border-ink group-has-checked:border-ink group-has-checked:bg-ink group-has-checked:text-paper"
                >
                  <svg viewBox="0 0 16 16" className="hidden size-3.5 group-has-checked:block" fill="none">
                    <path
                      d="M3 8.5l3 3 7-7"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span className="min-w-0 [overflow-wrap:anywhere]">
                  {sessionLabel(item)}
                  {item.deletion_date ? (
                    <span className="text-ink-secondary"> · {copy.exports.deletes(formatDay(item.deletion_date))}</span>
                  ) : null}
                </span>
              </label>
            ))}
            {choiceError ? (
              <p id="run-sessions-error" className="text-body-phone text-restordre">
                {choiceError}
              </p>
            ) : null}
          </fieldset>
          <TextField
            ref={keyRef}
            id="evaluation-key"
            name="evaluation-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            label={form.key}
            hint={form.keyHint}
            error={keyReason}
            onChange={() => {
              setDone(undefined);
              if (keyReason) setKeyReason(keyError(keyRef.current?.value ?? ""));
            }}
          />
          <ActionError message={run.isError ? runRefusal(run.error) : undefined} />
          <Button
            type="submit"
            variant="primary"
            unavailable={run.isPending}
            className="w-full sm:w-auto sm:self-start"
          >
            {form.submit}
          </Button>
          {done ? (
            <p
              ref={doneRef}
              tabIndex={-1}
              role="status"
              className="border-y border-ink-muted py-2 text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body"
            >
              {done}
            </p>
          ) : null}
        </form>
      )}
    </section>
  );
}

/** «Nøkkel»: the stored fingerprint, and the replacement with a new key (a secondary button). */
function KeySection() {
  const state = useKeyState();
  const replace = useReplaceKey();
  const [reason, setReason] = useState<string>();
  const [replaced, setReplaced] = useState(false);
  const fieldRef = useRef<HTMLInputElement>(null);
  const form = copy.key;
  const fingerprint = state.data?.fingerprint;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (replace.isPending) return;
    setReplaced(false);
    replace.reset();
    const key = fieldRef.current?.value ?? "";
    const found = keyError(key);
    setReason(found);
    if (found) {
      fieldRef.current?.focus();
      return;
    }
    replace.mutate(key.trim(), {
      onSuccess: () => setReplaced(true),
      onSettled: () => {
        if (fieldRef.current) fieldRef.current.value = "";
      },
    });
  }

  return (
    <section aria-labelledby="key-title" className="mt-12">
      <h2 id="key-title" className="text-headline text-ink">
        {form.title}
      </h2>
      <p className="mt-2 max-w-2xl text-body-phone text-ink lg:text-body">
        {state.isSuccess
          ? fingerprint && state.data.set_at
            ? form.stored(shortFingerprint(fingerprint), formatTime(state.data.set_at))
            : form.none
          : null}
      </p>
      <p className="mt-2 mb-5 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{form.lead}</p>
      <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-xl flex-col gap-5">
        <TextField
          ref={fieldRef}
          id="new-evaluation-key"
          name="new-evaluation-key"
          type="password"
          autoComplete="off"
          spellCheck={false}
          label={form.field}
          error={reason}
          onChange={() => {
            setReplaced(false);
            if (reason) setReason(keyError(fieldRef.current?.value ?? ""));
          }}
        />
        <ActionError message={replace.isError ? form.failed : undefined} />
        <Button type="submit" unavailable={replace.isPending} className="w-full sm:w-auto sm:self-start">
          {form.submit}
        </Button>
        {replaced ? (
          <p role="status" className="text-body-phone text-ink lg:text-body">
            {form.replaced}
          </p>
        ) : null}
      </form>
    </section>
  );
}

/** «Eksporter»: every run and refusal, newest first, with each Class session's deletion date. */
function ExportList() {
  const exports = useEvaluationExports();
  const columns = copy.exports.columns;
  const items = exports.data?.items ?? [];
  return (
    <section aria-labelledby="exports-title" className="mt-12 @container">
      <h2 id="exports-title" className="mb-4 text-headline text-ink">
        {copy.exports.title}
      </h2>
      {exports.isPending ? <Skeleton heading={false} rows={2} columns={4} /> : null}
      {exports.isError ? (
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
      ) : null}
      {exports.isSuccess && items.length === 0 ? (
        <p className="text-body-phone text-ink lg:text-body">{copy.exports.empty}</p>
      ) : null}
      {items.length > 0 ? (
        <table className={TABLE}>
          <thead className="@max-[60em]:hidden">
            <tr className="border-b border-axis">
              {[columns.time, columns.actor, columns.sessions, columns.fingerprint, columns.outcome].map((heading) => (
                <th key={heading} scope="col" className={HEAD}>
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
            {items.map((item) => (
              <tr key={item.id} className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3">
                <Cell label={columns.time}>
                  <span className="@min-[60em]:whitespace-nowrap">{formatTime(item.occurred_at)}</span>
                </Cell>
                <Cell label={columns.actor}>
                  <span className="[overflow-wrap:anywhere]">{item.actor_name ?? nb.admin.audit.unknown}</span>
                </Cell>
                <Cell label={columns.sessions}>
                  <ul className="flex flex-col gap-1">
                    {item.class_sessions.map((found) => (
                      <li key={found.id} className="[overflow-wrap:anywhere]">
                        {found.class_name !== null && found.number !== null
                          ? sessionLabel({
                              class_name: found.class_name,
                              number: found.number,
                            })
                          : copy.exports.gone}
                        <span className="block text-ink-secondary">
                          {found.deletion_date
                            ? copy.exports.deletes(formatDay(found.deletion_date))
                            : copy.exports.noDeletion}
                        </span>
                      </li>
                    ))}
                  </ul>
                </Cell>
                <Cell label={columns.fingerprint}>
                  <span className="@min-[60em]:whitespace-nowrap">
                    {item.key_fingerprint ? shortFingerprint(item.key_fingerprint) : nb.admin.audit.noChange}
                  </span>
                </Cell>
                <Cell label={columns.outcome}>{outcomeText(item.outcome)}</Cell>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
