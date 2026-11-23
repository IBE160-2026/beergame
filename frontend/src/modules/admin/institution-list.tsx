"use client";

import { type FormEvent, Fragment, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { Switch } from "@/components/switch";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { ApiRequestError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

import {
  type Institution,
  institutionsKey,
  useInstitutions,
  useMarkOperator,
  useRecordProcessingAgreement,
  useRenameInstitution,
  useSetNoLetter,
} from "./api";
import { formatDay, todayInOslo } from "./evaluation";
import {
  cleanName,
  nameError,
  type ProcessingAgreementErrors,
  processingAgreementErrors,
  refusalForField,
  SIGNED_BY_MAX_LENGTH,
} from "./institutions";
import { formatDate } from "./invitations";
import { Cell, type RowLine, RowMessage } from "./user-list";

const copy = nb.admin.institutions;

/**
 * «Alle Institusjoner» (Story 3.11, FR-3): name and creation date, newest first, one page of the
 * list envelope at a time. Each row has one button that opens an inline rename form in its place;
 * a saved name closes it, focus returns to the row's button and the row says what changed. Below
 * laptop width every row is one block with each field labelled, as the User list. The row line
 * goes when a create starts in the form (`otherStarted` counts those starts; `onStart` tells the
 * page that a rename starts).
 */
export function InstitutionList({ onStart, otherStarted = 0 }: { onStart?: () => void; otherStarted?: number } = {}) {
  const institutions = useInstitutions();
  const pageState = usePageState(institutions, institutionsKey);
  const moreFailed = institutions.isFetchNextPageError;
  const phase = moreFailed ? "ready" : pageState.phase;
  const [editing, setEditing] = useState<string>();
  const [line, setLine] = useState<RowLine>();
  const [focusRow, setFocusRow] = useState<{ id: string; n: number }>();
  const [agreementOpen, setAgreementOpen] = useState<string>();
  const [focusAgreement, setFocusAgreement] = useState<{ id: string; n: number }>();
  const items = institutions.data?.pages.flatMap((page) => page.items) ?? [];
  const markOperator = useMarkOperator();
  const noLetter = useSetNoLetter();

  useEffect(() => {
    if (focusRow) document.getElementById(`rename-${focusRow.id}`)?.focus();
  }, [focusRow]);
  useEffect(() => {
    if (focusAgreement) document.getElementById(`agreement-${focusAgreement.id}`)?.focus();
  }, [focusAgreement]);
  useEffect(() => {
    if (otherStarted) setLine(undefined);
  }, [otherStarted]);

  function close(id: string, renamed?: { from: string; to: Institution }) {
    setEditing(undefined);
    if (renamed) setLine({ key: id, text: copy.rename.renamed(renamed.from, renamed.to.name), refused: false });
    setFocusRow((prev) => ({ id, n: (prev?.n ?? 0) + 1 }));
  }

  function closeAgreement(institution: Institution, saved: boolean) {
    setAgreementOpen(undefined);
    if (saved) setLine({ key: institution.id, text: copy.processingAgreement.saved(institution.name), refused: false });
    setFocusAgreement((prev) => ({ id: institution.id, n: (prev?.n ?? 0) + 1 }));
  }

  return (
    <div className="@container">
      {phase === "loading" || phase === "slow" ? (
        <div>
          <Skeleton heading={false} rows={3} columns={3} />
          <LoadingNote visible={phase === "slow"} />
        </div>
      ) : null}
      {phase === "failed" ? (
        <div className="flex flex-col items-start gap-3">
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {nb.system.pageError}
          </p>
          <Button onClick={pageState.retry}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {phase === "ready" ? (
        <>
          {items.length === 0 ? <p className="text-body-phone text-ink lg:text-body">{copy.list.empty}</p> : null}
          {items.length > 0 ? (
            <table className="w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop">
              <thead className="@max-[60em]:hidden">
                <tr className="border-b border-axis">
                  {/* Opprettet has a fixed width, so the date column stays put whatever the names. */}
                  {[
                    copy.list.columns.name,
                    copy.list.columns.created,
                    copy.operator.column,
                    copy.noLetter.column,
                    copy.processingAgreement.column,
                    copy.list.columns.actions,
                  ].map((heading) => (
                    <th
                      key={heading}
                      scope="col"
                      className={`py-2 pr-6 align-bottom text-label font-semibold text-ink ${heading === copy.list.columns.created ? "w-[9em]" : ""}`}
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
                {items.map((institution) => (
                  <Fragment key={institution.id}>
                    <tr
                      className={cn(
                        "align-baseline @max-[60em]:block @max-[60em]:py-3",
                        agreementOpen === institution.id ? "@max-[60em]:pb-0" : "border-b border-hairline",
                      )}
                    >
                      <Cell label={copy.list.columns.name}>
                        <span className="font-semibold [overflow-wrap:anywhere]">{institution.name}</span>
                      </Cell>
                      <Cell label={copy.list.columns.created}>
                        <span className="@min-[60em]:whitespace-nowrap">{formatDate(institution.created_at)}</span>
                      </Cell>
                      <Cell label={copy.operator.column}>
                        {/* The operator's own Institution (Story 12.7): named in text; the others
                          take the mark with one button, and it moves from the one that held it. */}
                        {institution.operator_owned ? (
                          <span className="font-semibold">{copy.operator.label}</span>
                        ) : (
                          <Button
                            className="[overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                            unavailable={markOperator.isPending}
                            onClick={() => {
                              if (markOperator.isPending) return;
                              setLine(undefined);
                              onStart?.();
                              markOperator.mutate(institution.id, {
                                onSuccess: (marked) =>
                                  setLine({
                                    key: institution.id,
                                    text: copy.operator.marked(marked.name),
                                    refused: false,
                                  }),
                                onError: () =>
                                  setLine({ key: institution.id, text: copy.operator.failed, refused: true }),
                              });
                            }}
                          >
                            {copy.operator.mark(institution.name)}
                          </Button>
                        )}
                      </Cell>
                      <Cell label={copy.noLetter.column}>
                        {/* Story 12.6 (FR-56, FR-3): the data protection officer's Bryter, saved at
                          once; on, no Class session of the Institution shows a letter. */}
                        <span id={`no-letter-${institution.id}`} className="sr-only">
                          {copy.noLetter.name(institution.name)}
                        </span>
                        <Switch
                          id={`no-letter-switch-${institution.id}`}
                          labelledBy={`no-letter-${institution.id}`}
                          checked={
                            noLetter.isPending && noLetter.variables?.id === institution.id
                              ? noLetter.variables.on
                              : institution.no_letter
                          }
                          onChange={(on) => {
                            if (noLetter.isPending) return;
                            setLine(undefined);
                            onStart?.();
                            noLetter.mutate(
                              { id: institution.id, on },
                              {
                                onSuccess: (saved) =>
                                  setLine({
                                    key: institution.id,
                                    text: copy.noLetter.saved(saved.name, saved.no_letter),
                                    refused: false,
                                  }),
                                onError: () =>
                                  setLine({ key: institution.id, text: copy.noLetter.failed, refused: true }),
                              },
                            );
                          }}
                        >
                          {(
                            noLetter.isPending && noLetter.variables?.id === institution.id
                              ? noLetter.variables.on
                              : institution.no_letter
                          )
                            ? copy.noLetter.on
                            : copy.noLetter.off}
                        </Switch>
                      </Cell>
                      <Cell label={copy.processingAgreement.column}>
                        {/* Story 15.12 (FR-8): who signed and the day, or that none is recorded;
                          the button opens the form in a row of its own under this one. */}
                        <span className="block [overflow-wrap:anywhere]">
                          {institution.processing_agreement
                            ? copy.processingAgreement.signed(
                                institution.processing_agreement.signed_by,
                                formatDay(institution.processing_agreement.signed_on),
                              )
                            : institution.operator_owned
                              ? copy.processingAgreement.notNeeded
                              : copy.processingAgreement.none}
                        </span>
                        {agreementOpen === institution.id ? null : (
                          <Button
                            id={`agreement-${institution.id}`}
                            className="mt-2 [overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                            onClick={() => {
                              setLine(undefined);
                              onStart?.();
                              setEditing(undefined);
                              setAgreementOpen(institution.id);
                            }}
                          >
                            {institution.processing_agreement
                              ? copy.processingAgreement.change(institution.name)
                              : copy.processingAgreement.record(institution.name)}
                          </Button>
                        )}
                      </Cell>
                      <td className="py-3 @max-[60em]:block @max-[60em]:pt-2 @max-[60em]:pb-0 @min-[60em]:w-[24em]">
                        {editing === institution.id ? (
                          <RenameForm institution={institution} onDone={(renamed) => close(institution.id, renamed)} />
                        ) : (
                          <Button
                            id={`rename-${institution.id}`}
                            className="[overflow-wrap:anywhere] @max-[60em]:w-full @min-[60em]:px-3 @min-[60em]:text-left"
                            onClick={() => {
                              setLine(undefined);
                              onStart?.();
                              setAgreementOpen(undefined);
                              setEditing(institution.id);
                            }}
                          >
                            {copy.rename.open(institution.name)}
                          </Button>
                        )}
                        <RowMessage
                          line={line?.key === institution.id && editing !== institution.id ? line : undefined}
                        />
                      </td>
                    </tr>
                    {agreementOpen === institution.id ? (
                      // The form takes the row's full width under it, not one column's.
                      <tr className="border-b border-hairline @max-[60em]:block">
                        <td colSpan={6} className="pt-1 pb-6 @max-[60em]:block">
                          <AgreementForm
                            institution={institution}
                            onDone={(saved) => closeAgreement(institution, saved)}
                          />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                ))}
              </tbody>
            </table>
          ) : null}
          {moreFailed ? <ActionError message={copy.list.moreFailed} className="mt-4" /> : null}
          {institutions.hasNextPage ? (
            <Button
              className="mt-4"
              unavailable={institutions.isFetchingNextPage}
              onClick={() => void institutions.fetchNextPage()}
            >
              {copy.list.more}
            </Button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

/** The inline rename form of one row: the Tekstfelt prefilled with the name, «Lagre navnet» and
 * «Avbryt». A bad or taken name shows the reason under the field, which follows what is typed. */
function RenameForm({
  institution,
  onDone,
}: {
  institution: Institution;
  onDone: (renamed?: { from: string; to: Institution }) => void;
}) {
  const rename = useRenameInstitution();
  const [error, setError] = useState<string>();
  const [submitted, setSubmitted] = useState(false);
  const fieldRef = useRef<HTMLInputElement>(null);
  const fieldId = `institution-name-${institution.id}`;

  useEffect(() => {
    fieldRef.current?.focus();
    fieldRef.current?.select();
  }, []);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (rename.isPending) return;
    const value = fieldRef.current?.value ?? "";
    const reason = nameError(value);
    setError(reason);
    setSubmitted(true);
    rename.reset();
    if (reason) {
      fieldRef.current?.focus();
      return;
    }
    rename.mutate(
      { id: institution.id, name: cleanName(value) },
      {
        onSuccess: (updated) =>
          onDone(updated.name === institution.name ? undefined : { from: institution.name, to: updated }),
        onError: (failure) => {
          const field = refusalForField(failure);
          if (field) {
            setError(field);
            fieldRef.current?.focus();
          }
        },
      },
    );
  }

  const general = rename.isError && !refusalForField(rename.error) ? copy.rename.failed : undefined;

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex flex-col gap-3">
      <TextField
        ref={fieldRef}
        id={fieldId}
        name="name"
        autoComplete="off"
        label={copy.rename.field(institution.name)}
        className="[overflow-wrap:anywhere]"
        defaultValue={institution.name}
        error={error}
        onChange={() => {
          if (submitted) setError(nameError(fieldRef.current?.value ?? ""));
        }}
        onKeyDown={(event) => {
          // A save under way finishes first: closing then would lose its result line.
          if (event.key === "Escape" && !rename.isPending) onDone();
        }}
      />
      <ActionError message={general} />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Button type="submit" unavailable={rename.isPending} className="@max-[60em]:w-full">
          {copy.rename.save}
        </Button>
        <button
          type="button"
          aria-disabled={rename.isPending ? true : undefined}
          onClick={() => {
            if (!rename.isPending) onDone();
          }}
          className="inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink"
        >
          {copy.rename.cancel}
        </button>
      </div>
    </form>
  );
}

/** The inline data processing agreement form of one Institution (Story 15.12): who signed for
 * it, the day, «Lagre avtalen» and «Avbryt». Each field's reason stands under it. */
function AgreementForm({ institution, onDone }: { institution: Institution; onDone: (saved: boolean) => void }) {
  const record = useRecordProcessingAgreement();
  const form = copy.processingAgreement;
  const [values, setValues] = useState({
    signedBy: institution.processing_agreement?.signed_by ?? "",
    signedOn: institution.processing_agreement?.signed_on ?? "",
  });
  const [errors, setErrors] = useState<ProcessingAgreementErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const firstRef = useRef<HTMLInputElement>(null);
  const id = (name: string) => `${name}-${institution.id}`;
  const title = institution.processing_agreement ? form.change(institution.name) : form.record(institution.name);

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  function change(next: Partial<typeof values>) {
    const merged = { ...values, ...next };
    setValues(merged);
    if (submitted) setErrors(processingAgreementErrors(merged, todayInOslo()));
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (record.isPending) return;
    const found = processingAgreementErrors(values, todayInOslo());
    setErrors(found);
    setSubmitted(true);
    record.reset();
    const first = (["signedBy", "signedOn"] as const).find((name) => found[name]);
    if (first) {
      document.getElementById(id(first))?.focus();
      return;
    }
    record.mutate(
      { id: institution.id, body: { signed_by: values.signedBy.trim(), signed_on: values.signedOn } },
      {
        onSuccess: () => onDone(true),
        onError: (failure) => {
          // The api's clock has the last word on «not after today»: its reason stands under the field.
          if (dayRefused(failure)) {
            setErrors({ signedOn: form.inFuture });
            document.getElementById(id("signedOn"))?.focus();
          }
        },
      },
    );
  }

  return (
    <form
      method="post"
      noValidate
      onSubmit={onSubmit}
      aria-label={title}
      className="grid max-w-3xl grid-cols-1 items-start gap-4 @min-[60em]:grid-cols-2 @min-[60em]:gap-x-6"
    >
      <TextField
        ref={firstRef}
        id={id("signedBy")}
        label={form.signedBy}
        hint={form.signedByHint}
        autoComplete="off"
        maxLength={SIGNED_BY_MAX_LENGTH}
        value={values.signedBy}
        error={errors.signedBy}
        onChange={(event) => change({ signedBy: event.target.value })}
      />
      <TextField
        id={id("signedOn")}
        type="date"
        label={form.signedOn}
        max={todayInOslo()}
        value={values.signedOn}
        error={errors.signedOn}
        onChange={(event) => change({ signedOn: event.target.value })}
      />
      <ActionError
        message={record.isError && !dayRefused(record.error) ? form.failed : undefined}
        className="@min-[60em]:col-span-2"
      />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 @min-[60em]:col-span-2">
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

/** The api refused the day as after today in Europe/Oslo (422 `fields.signed_on` = `in_future`). */
function dayRefused(error: unknown): boolean {
  return error instanceof ApiRequestError && error.fields.signed_on === "in_future";
}
