"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";

import {
  type AccountRole,
  type ListedUser,
  useChangeRole,
  useChangeStatus,
  useDeleteUser,
  usersKey,
  useUsers,
} from "./api";
import {
  changedLine,
  DELETE_REFERENCE_MAX_LENGTH,
  deleteReference,
  deleteReferenceError,
  deleteRefusal,
  firstName,
  holds,
  refusalLine,
  ROLES,
  roleButtonLabel,
  rolesText,
  statusButtonLabel,
  statusChangedLine,
  statusRefusalLine,
} from "./user-roles";

const copy = nb.admin.users.list;

/** How long the search waits after the last key before it asks the api. */
export const SEARCH_DELAY_MS = 250;

/** The api's longest search text (`SEARCH_MAX_LENGTH` in `identity/schemas.py`). */
const SEARCH_MAX_LENGTH = 200;

export type RowLine = { key: string; text: string; refused: boolean };

/**
 * The User list on «Brukere og roller» (Story 3.9, FR-2, FR-3, UX-DR57, UX-DR75): a search field
 * and a table of Users with their roles and status, one page of the list envelope at a time.
 * Below laptop width every row is one block with each field labelled. Each row has one button
 * per account role, stating its effect and the User's first name; pressing it changes the role
 * at once, with no dialog, and one status button that deactivates or reactivates the User
 * (Story 3.10). The row then says what changed, or why nothing did. «Slett …» opens the row's
 * deletion (Story 15.2): the reference to the Institution's instruction and one button that
 * states the consequence and deletes on one press; the row then leaves the list and the line
 * above it says so.
 */
export function UserList({ selfId }: { selfId: string }) {
  const [typed, setTyped] = useState("");
  const [search, setSearch] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(typed.trim()), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [typed]);

  const users = useUsers(search);
  const pageState = usePageState(users, usersKey(search));
  // A failed «Vis flere» keeps the rows already shown; only the first page decides the page state.
  const moreFailed = users.isFetchNextPageError;
  const phase = moreFailed ? "ready" : pageState.phase;
  const retry = pageState.retry;
  const change = useChangeRole(selfId);
  const status = useChangeStatus();
  const removal = useDeleteUser();
  const busy = change.isPending || status.isPending || removal.isPending;
  const [line, setLine] = useState<RowLine>();
  const [deleting, setDeleting] = useState<string>();
  const [deletedLine, setDeletedLine] = useState<string>();
  const deletedRef = useRef<HTMLDivElement>(null);
  const items = users.data?.pages.flatMap((page) => page.items) ?? [];

  function press(user: ListedUser, role: AccountRole) {
    if (busy) return;
    const grant = !holds(user, role);
    // A new press ends the earlier line, so it never stands beside a new result.
    setLine(undefined);
    setDeletedLine(undefined);
    change.mutate(
      { user, role, grant },
      {
        onSuccess: (updated) => setLine({ key: user.id, text: changedLine(updated, role, grant), refused: false }),
        onError: (error) => setLine({ key: user.id, text: refusalLine(error, user), refused: true }),
      },
    );
  }

  function toggleDelete(user: ListedUser) {
    if (busy) return;
    setLine(undefined);
    setDeletedLine(undefined);
    setDeleting((open) => (open === user.id ? undefined : user.id));
  }

  function pressDelete(user: ListedUser, reference: string, refused: (field: string) => void) {
    if (busy) return;
    setLine(undefined);
    removal.mutate(
      { user, reference },
      {
        onSuccess: () => {
          setDeleting(undefined);
          setDeletedLine(copy.delete.deleted(firstName(user.name)));
          // The row and its buttons are gone: focus moves to the line that says so.
          window.requestAnimationFrame(() => deletedRef.current?.focus());
        },
        onError: (error) => {
          const { field, line: text } = deleteRefusal(error, user, selfId);
          if (field) refused(field);
          if (text) setLine({ key: user.id, text, refused: true });
        },
      },
    );
  }

  function pressStatus(user: ListedUser) {
    if (busy) return;
    setLine(undefined);
    setDeletedLine(undefined);
    status.mutate(user, {
      onSuccess: (updated) => setLine({ key: user.id, text: statusChangedLine(updated), refused: false }),
      onError: (error) => setLine({ key: user.id, text: statusRefusalLine(error, user, selfId), refused: true }),
    });
  }

  return (
    // A container: the table turns into labelled blocks by the room it has in text widths, so
    // 200 % text gets the blocks too (a media query would not see the text size).
    <div className="@container">
      <div role="search" className="max-w-md">
        <TextField
          id="user-search"
          type="search"
          autoComplete="off"
          spellCheck={false}
          label={copy.search}
          maxLength={SEARCH_MAX_LENGTH}
          value={typed}
          onChange={(event) => {
            // The row line speaks of the list as it was; it goes as soon as the search changes.
            setLine(undefined);
            setDeletedLine(undefined);
            setTyped(event.target.value);
          }}
        />
      </div>
      {phase === "loading" || phase === "slow" ? (
        <div className="mt-6">
          <Skeleton heading={false} rows={4} columns={4} />
          <LoadingNote visible={phase === "slow"} />
        </div>
      ) : null}
      {phase === "failed" ? (
        <div className="mt-6 flex flex-col items-start gap-3">
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {nb.system.pageError}
          </p>
          <Button onClick={retry}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {phase === "ready" ? (
        <>
          {/* One polite status region, always there so a new line is announced. After a delete it
              holds a notice between two rules, and «Ingen treff.» under it when the search now
              finds no one; both are read out. */}
          <div
            ref={deletedRef}
            tabIndex={-1}
            role="status"
            className="mt-6 flex flex-col gap-4 text-body-phone text-ink outline-none lg:text-body"
          >
            {deletedLine ? (
              <p className="max-w-2xl border-y border-ink-muted py-2" data-deleted-line="">
                {deletedLine}
              </p>
            ) : null}
            {items.length === 0 && (!deletedLine || search) ? <p>{copy.noMatches}</p> : null}
          </div>
          {items.length > 0 ? (
            <table className="w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop">
              <thead className="@max-[60em]:hidden">
                <tr className="border-b border-axis">
                  {[copy.columns.name, copy.columns.email, copy.columns.roles, copy.columns.status, copy.columns.actions].map(
                    (heading) => (
                      <th key={heading} scope="col" className="py-2 pr-6 align-bottom text-label font-semibold text-ink">
                        {heading}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis">
                {items.map((user) => (
                  <tr key={user.id} className="border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3">
                    <Cell label={copy.columns.name}>
                      <span className="font-semibold">{user.name}</span>
                    </Cell>
                    <Cell label={copy.columns.email}>
                      <span className="[overflow-wrap:anywhere]">{user.email}</span>
                    </Cell>
                    <Cell label={copy.columns.roles}>
                      {/* «Faglærer, Admin» stays on one line in the table; the e-mail column gives way. */}
                      <span className="@min-[60em]:whitespace-nowrap">{rolesText(user)}</span>
                    </Cell>
                    <Cell label={copy.columns.status}>
                      <span className={user.is_active ? undefined : "text-ink-secondary"}>
                        {user.is_active ? copy.active : copy.deactivated}
                      </span>
                    </Cell>
                    <td className="py-3 @max-[60em]:block @max-[60em]:pt-2 @max-[60em]:pb-0">
                      {/* Capped, so the buttons stack instead of squeezing the name and e-mail. */}
                      <div className="flex flex-wrap gap-2 @min-[60em]:max-w-[30em]">
                        {ROLES.map((role) => (
                          <Button
                            key={role}
                            className="@max-[60em]:w-full @max-[60em]:[overflow-wrap:anywhere] @min-[60em]:px-3"
                            unavailable={busy}
                            onClick={() => press(user, role)}
                          >
                            {roleButtonLabel(user, role)}
                          </Button>
                        ))}
                        <Button
                          className="@max-[60em]:w-full @max-[60em]:[overflow-wrap:anywhere] @min-[60em]:max-w-[22em] @min-[60em]:px-3 @min-[60em]:text-left"
                          unavailable={busy}
                          onClick={() => pressStatus(user)}
                        >
                          {statusButtonLabel(user)}
                        </Button>
                        <Button
                          className="@max-[60em]:w-full @max-[60em]:[overflow-wrap:anywhere] @min-[60em]:px-3"
                          unavailable={busy}
                          aria-expanded={deleting === user.id}
                          aria-controls={`delete-${user.id}`}
                          onClick={() => toggleDelete(user)}
                        >
                          {deleting === user.id ? copy.delete.close : copy.delete.open(firstName(user.name))}
                        </Button>
                      </div>
                      {deleting === user.id ? (
                        <DeletePanel
                          user={user}
                          busy={busy}
                          onDelete={(reference, refused) => pressDelete(user, reference, refused)}
                        />
                      ) : null}
                      <RowMessage line={line?.key === user.id ? line : undefined} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {moreFailed ? <ActionError message={copy.moreFailed} className="mt-4" /> : null}
          {users.hasNextPage ? (
            <Button
              className="mt-4"
              unavailable={users.isFetchingNextPage}
              onClick={() => void users.fetchNextPage()}
            >
              {copy.more}
            </Button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

/** A table cell; below laptop width it is a labelled line of the row's block. A long word (a
 * name, «Testmåling») breaks rather than push a phone page sideways at 200 % text (Story 15.13). */
export function Cell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <td className="py-3 pr-6 @max-[60em]:flex @max-[60em]:gap-3 @max-[60em]:py-1 @max-[60em]:pr-0">
      <span className="w-20 shrink-0 text-ink-secondary @min-[60em]:hidden">{label}</span>
      <span className="min-w-0 @max-[60em]:[overflow-wrap:anywhere]">{children}</span>
    </td>
  );
}

/** The row's result line, or its refusal with `role="alert"` (as `ActionError`), announced as
 * it appears; focus stays on the pressed button. */
export function RowMessage({ line }: { line?: RowLine }) {
  if (!line) return null;
  return (
    <p
      role={line.refused ? "alert" : "status"}
      className={`mt-2 max-w-sm text-body-phone lg:text-body ${line.refused ? "text-restordre" : "text-ink"}`}
    >
      {line.text}
    </p>
  );
}

/** A row's deletion (Story 15.2, FR-76, UX-DR9): the reference to the Institution's instruction,
 * checked before it is sent, and the one button that deletes, stating the consequence. It is the
 * irreversible action, so it is the primary button; no dialog follows the press. */
function DeletePanel({
  user,
  busy,
  onDelete,
}: {
  user: ListedUser;
  busy: boolean;
  onDelete: (reference: string, refused: (field: string) => void) => void;
}) {
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string>();
  const field = useRef<HTMLInputElement>(null);
  return (
    <div id={`delete-${user.id}`} className="mt-3 flex max-w-md flex-col items-start gap-3">
      <TextField
        ref={field}
        id={`delete-reference-${user.id}`}
        className="w-full"
        label={copy.delete.reference}
        hint={copy.delete.hint}
        autoComplete="off"
        spellCheck={false}
        maxLength={4 * DELETE_REFERENCE_MAX_LENGTH}
        value={typed}
        error={error}
        onChange={(event) => {
          setError(undefined);
          setTyped(event.target.value);
        }}
      />
      <Button
        variant="primary"
        className="w-full text-left"
        unavailable={busy}
        onClick={() => {
          const invalid = deleteReferenceError(typed);
          setError(invalid);
          if (invalid) {
            field.current?.focus();
            return;
          }
          onDelete(deleteReference(typed), (reason) => {
            setError(reason);
            field.current?.focus();
          });
        }}
      >
        {copy.delete.submit(firstName(user.name))}
      </Button>
    </div>
  );
}
