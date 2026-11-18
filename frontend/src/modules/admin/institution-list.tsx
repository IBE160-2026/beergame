"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";

import { type Institution, institutionsKey, useInstitutions, useRenameInstitution } from "./api";
import { cleanName, nameError, refusalForField } from "./institutions";
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
  const items = institutions.data?.pages.flatMap((page) => page.items) ?? [];

  useEffect(() => {
    if (focusRow) document.getElementById(`rename-${focusRow.id}`)?.focus();
  }, [focusRow]);
  useEffect(() => {
    if (otherStarted) setLine(undefined);
  }, [otherStarted]);

  function close(id: string, renamed?: { from: string; to: Institution }) {
    setEditing(undefined);
    if (renamed) setLine({ key: id, text: copy.rename.renamed(renamed.from, renamed.to.name), refused: false });
    setFocusRow((prev) => ({ id, n: (prev?.n ?? 0) + 1 }));
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
                  {[copy.list.columns.name, copy.list.columns.created, copy.list.columns.actions].map((heading) => (
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
                  <tr
                    key={institution.id}
                    className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3"
                  >
                    <Cell label={copy.list.columns.name}>
                      <span className="font-semibold [overflow-wrap:anywhere]">{institution.name}</span>
                    </Cell>
                    <Cell label={copy.list.columns.created}>
                      <span className="@min-[60em]:whitespace-nowrap">{formatDate(institution.created_at)}</span>
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
                            setEditing(institution.id);
                          }}
                        >
                          {copy.rename.open(institution.name)}
                        </Button>
                      )}
                      <RowMessage line={line?.key === institution.id && editing !== institution.id ? line : undefined} />
                    </td>
                  </tr>
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
