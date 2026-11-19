"use client";

import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, type ReactNode, type Ref, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { errorCode, useAction } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classPath, classStaffPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import {
  addClassLecturer,
  type ClassStaff,
  classesKey,
  classKey,
  classStaffKey,
  inviteClassAssistant,
  removeClassStaff,
  type StaffAssistant,
  type StaffLecturer,
  useClass,
  useClassStaff,
  withdrawAssistantInvitation,
} from "./api";
import { EntryResult, LINK_BUTTON } from "./roster-entry-forms";
import { assistantStatus, personLabel, staffRefusal } from "./staff";

const copy = nb.classes.staff;
const CLASS_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PANEL = "flex w-full max-w-md flex-col items-start gap-4 rounded-sm border border-axis px-4 py-4";

/**
 * «Faglærere og assistenter» (Story 4.9, FR-10, UX-DR56): the Class's Faglærere (co-owners, with
 * the owner's rights) and Assistenter, each with a status in text, «Legg til Faglærer» and
 * «Inviter Assistent» as in-place forms (one at a time), and «Fjern» with its consequence above
 * the button. Only the Class's Faglærere reach it: an Assistent, another Lecturer, a Class that
 * does not exist and an address that names none all see the permission-denied page (FR-5).
 */
export function StaffPage({ classId }: { classId: string }) {
  const named = CLASS_ID.test(classId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <StaffView classId={classId} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

const forbidden = (error: unknown) => error instanceof ApiRequestError && error.code === "forbidden";

function StaffView({ classId, user, updatedAt }: { classId: string; user: SessionUser; updatedAt: number }) {
  const found = useClass(classId);
  const staff = useClassStaff(classId);
  const { phase, retry } = usePageState(staff, classStaffKey(classId));
  const item = found.data;
  // The Class's own read failing (not refused) is a page error too, retried with the list.
  const failed = found.isError && !forbidden(found.error);
  if (forbidden(found.error) || forbidden(staff.error) || (item && !item.can_manage)) {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const crumbs = item
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: item.name, href: classPath(item.id) },
        { label: copy.title, href: classStaffPath(item.id) },
      ] as const)
    : undefined;
  const ready = item && staff.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={ready ? "ready" : failed ? "failed" : phase === "ready" ? "loading" : phase}
      onRetry={() => {
        retry();
        if (failed) void found.refetch();
      }}
    >
      {ready ? <StaffLists classId={classId} data={staff.data} self={user.id} /> : null}
    </PageShell>
  );
}

type Open =
  | { kind: "lecturer" }
  | { kind: "assistant" }
  | { kind: "remove"; person: StaffLecturer | StaffAssistant; lecturer: boolean };

/** Every read a staff change moves: the list, the Class and the Lærerhjem. */
function invalidateStaff(queryClient: QueryClient, classId: string) {
  for (const key of [classStaffKey(classId), classKey(classId), classesKey]) {
    void queryClient.invalidateQueries({ queryKey: key, exact: true });
  }
}

const rowKey = (person: StaffLecturer | StaffAssistant) =>
  ("invitation_id" in person && person.invitation_id) || person.user_id || person.email;

function StaffLists({ classId, data, self }: { classId: string; data: ClassStaff; self: string }) {
  const [open, setOpen] = useState<Open | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const resultLine = useRef<HTMLParagraphElement>(null);
  const [focusResult, setFocusResult] = useState(0);
  useEffect(() => {
    if (focusResult) resultLine.current?.focus();
  }, [focusResult]);
  const today = todayIso();

  const start = (next: Open, from: HTMLButtonElement) => {
    setResult(null); // a new action clears the last result line
    opener.current = from;
    setOpen(next);
  };
  const cancel = () => {
    setOpen(null);
    opener.current?.focus();
  };
  const done = (text: string) => {
    setOpen(null);
    setResult(text);
    setFocusResult((n) => n + 1);
  };
  const isOpen = (person: StaffLecturer | StaffAssistant) =>
    open?.kind === "remove" && rowKey(open.person) === rowKey(person);

  const removeButton = (person: StaffLecturer | StaffAssistant, lecturer: boolean) => (
    <button
      type="button"
      className={LINK_BUTTON}
      aria-label={copy.removeFor(personLabel(person))}
      aria-expanded={isOpen(person)}
      onClick={(event) => start({ kind: "remove", person, lecturer }, event.currentTarget)}
    >
      {copy.remove}
    </button>
  );
  const panel = (person: StaffLecturer | StaffAssistant) =>
    open?.kind === "remove" && isOpen(person) ? (
      <div className="mt-2 mb-2">
        <RemovePanel
          classId={classId}
          person={open.person}
          lecturer={open.lecturer}
          self={open.person.user_id === self}
          onDone={done}
          onCancel={cancel}
        />
      </div>
    ) : null;

  return (
    <div className="mt-8 flex max-w-4xl flex-col gap-10">
      {result ? <EntryResult text={result} ref={resultLine} /> : null}
      <section aria-labelledby="lecturers-title">
        <h2 id="lecturers-title" className="text-headline text-ink">
          {copy.lecturers}
        </h2>
        <p className="mt-1 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lecturersLead}</p>
        <ul className="mt-4 border-t border-hairline">
          {data.lecturers.map((person) => (
            <li key={person.user_id} className="border-b border-hairline py-2">
              <Row label={personLabel(person)} status={copy.active} action={removeButton(person, true)} />
              {panel(person)}
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-col items-start gap-4">
          <button
            type="button"
            className={LINK_BUTTON}
            aria-expanded={open?.kind === "lecturer"}
            onClick={(event) => start({ kind: "lecturer" }, event.currentTarget)}
          >
            {copy.addLecturer}
          </button>
          {open?.kind === "lecturer" ? (
            <EmailForm
              id="staff-lecturer"
              title={copy.addLecturerTitle}
              lead={copy.addLecturerLead}
              submit={copy.addLecturerSubmit}
              send={(email) => addClassLecturer(classId, email)}
              classId={classId}
              onDone={(added) => done(copy.lecturerAdded(personLabel(added as StaffLecturer)))}
              onCancel={cancel}
            />
          ) : null}
        </div>
      </section>
      <section aria-labelledby="assistants-title">
        <h2 id="assistants-title" className="text-headline text-ink">
          {copy.assistants}
        </h2>
        <p className="mt-1 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.assistantScope}</p>
        {data.assistants.length === 0 ? (
          <p className="mt-4 text-body-phone text-ink-secondary lg:text-body">{copy.noAssistants}</p>
        ) : (
          <ul className="mt-4 border-t border-hairline">
            {data.assistants.map((person) => (
              <li key={rowKey(person)} className="border-b border-hairline py-2">
                <Row
                  label={personLabel(person)}
                  status={assistantStatus(person, today)}
                  action={removeButton(person, false)}
                />
                {panel(person)}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-4 flex flex-col items-start gap-4">
          <button
            type="button"
            className={LINK_BUTTON}
            aria-expanded={open?.kind === "assistant"}
            onClick={(event) => start({ kind: "assistant" }, event.currentTarget)}
          >
            {copy.inviteAssistant}
          </button>
          {open?.kind === "assistant" ? (
            <EmailForm
              id="staff-assistant"
              title={copy.inviteAssistantTitle}
              lead={copy.assistantScope}
              submit={copy.inviteAssistantSubmit}
              send={(email) => inviteClassAssistant(classId, email)}
              classId={classId}
              onDone={(sent) => done(copy.assistantInvited((sent as StaffAssistant).email))}
              onCancel={cancel}
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}

/** One person: name and address, the status in text, and the action. Stacks at 320 px. */
function Row({ label, status, action }: { label: string; status: string; action: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 sm:grid sm:min-h-tap-target-min sm:grid-cols-[minmax(0,1fr)_minmax(0,16rem)_auto] sm:items-center sm:gap-x-4">
      <span className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">{label}</span>
      <span className="text-body-phone text-ink-secondary lg:text-body">{status}</span>
      <span className="sm:justify-self-end">{action}</span>
    </div>
  );
}

/** «Legg til Faglærer» or «Inviter Assistent» in place: one address, its refusal beside the field,
 * cleared as the Faglærer types. Focus moves to the field when it opens and after a refusal. */
function EmailForm({
  id,
  title,
  lead,
  submit,
  send,
  classId,
  onDone,
  onCancel,
}: {
  id: string;
  title: string;
  lead: string;
  submit: string;
  send: (email: string) => Promise<StaffLecturer | StaffAssistant>;
  classId: string;
  onDone: (result: StaffLecturer | StaffAssistant) => void;
  onCancel: () => void;
}) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string>();
  const field = useRef<HTMLInputElement>(null);
  const [focusField, setFocusField] = useState(0);
  useEffect(() => field.current?.focus(), [focusField]);
  const action = useAction({
    mutationFn: () => send(email),
    fallback: copy.failed,
    onSuccess: (result) => {
      invalidateStaff(queryClient, classId);
      onDone(result);
    },
  });
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (action.isPending) return;
    action.reset();
    action.mutate(undefined, {
      onError: (failure) => {
        const reason = staffRefusal(failure);
        if (reason) {
          setError(reason);
          setFocusField((n) => n + 1);
        }
      },
    });
  };
  return (
    <form noValidate aria-labelledby={`${id}-title`} className={PANEL} onSubmit={onSubmit}>
      <h3 id={`${id}-title`} className="text-label text-ink">
        {title}
      </h3>
      <p className="text-body-phone text-ink-secondary">{lead}</p>
      <TextField
        id={`${id}-email`}
        ref={field}
        label={copy.email}
        type="email"
        inputMode="email"
        autoComplete="off"
        spellCheck={false}
        value={email}
        error={error}
        onChange={(event) => {
          setEmail(event.target.value);
          setError(undefined);
          if (action.isError) action.reset();
        }}
        className="w-full"
      />
      <Buttons
        submit={action.isPending ? copy.saving : submit}
        pending={action.isPending}
        onCancel={() => {
          if (!action.isPending) onCancel();
        }}
      />
      <ActionError message={staffRefusal(action.error) ? undefined : action.errorMessage} />
    </form>
  );
}

/** «Fjern» in place: the consequence above the button, before it is pressed. A Faglærer or an
 * active Assistent is taken off the Class; an Invitation not accepted is withdrawn. */
function RemovePanel({
  classId,
  person,
  lecturer,
  self,
  onDone,
  onCancel,
}: {
  classId: string;
  person: StaffLecturer | StaffAssistant;
  lecturer: boolean;
  self: boolean;
  onDone: (text: string) => void;
  onCancel: () => void;
}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => button.current?.focus(), []);
  const invitation = "invitation_id" in person && person.invitation_id ? person.invitation_id : null;
  const who = personLabel(person);
  const action = useAction({
    mutationFn: () =>
      invitation ? withdrawAssistantInvitation(classId, invitation) : removeClassStaff(classId, person.user_id!),
    messages: { last_owner: copy.lastOwner },
    fallback: copy.removeFailed,
    onSuccess: () => {
      // Leaving the Class: its pages are no longer the User's. The Lærerhjem reads its list again;
      // this page's reads would only answer 403 before the move.
      if (self) {
        void queryClient.invalidateQueries({ queryKey: classesKey, exact: true });
        router.push(HOME_PATH.lecturerHome);
        return;
      }
      invalidateStaff(queryClient, classId);
      onDone(invitation ? copy.withdrawn(person.email) : copy.removed(who));
    },
  });
  const expired = "status" in person && person.status === "expired";
  const consequence = invitation
    ? expired
      ? copy.withdrawExpired(person.email)
      : copy.withdraw(person.email)
    : self
      ? copy.removeSelf
      : lecturer
        ? copy.removeLecturer(who)
        : copy.removeAssistant(who);
  const id = `staff-remove-${rowKey(person)}`;
  return (
    <div role="group" aria-labelledby={`${id}-title`} className={PANEL}>
      <h3 id={`${id}-title`} className="text-label text-ink [overflow-wrap:anywhere]">
        {copy.removeTitle(who)}
      </h3>
      <p id={`${id}-consequence`} className="text-body-phone text-ink [overflow-wrap:anywhere]">
        {consequence}
      </p>
      <Buttons
        ref={button}
        type="button"
        submit={action.isPending ? copy.saving : invitation ? copy.withdrawSubmit : copy.removeSubmit}
        describedBy={`${id}-consequence`}
        pending={action.isPending}
        onSubmit={() => {
          if (action.isPending) return;
          action.mutate(undefined, {
            onError: (failure) => {
              // Gone already: say so in the result line, and the list shows what the api has now.
              if (errorCode(failure) === "not_found") {
                invalidateStaff(queryClient, classId);
                onDone(copy.gone);
              }
            },
          });
        }}
        onCancel={() => {
          if (!action.isPending) onCancel();
        }}
      />
      <ActionError message={errorCode(action.error) === "not_found" ? undefined : action.errorMessage} />
    </div>
  );
}

function Buttons({
  submit,
  pending,
  onCancel,
  onSubmit,
  type = "submit",
  describedBy,
  ref,
}: {
  submit: string;
  pending: boolean;
  onCancel: () => void;
  onSubmit?: () => void;
  type?: "submit" | "button";
  describedBy?: string;
  ref?: Ref<HTMLButtonElement>;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
      <Button ref={ref} type={type} variant="primary" unavailable={pending} aria-describedby={describedBy} onClick={onSubmit}>
        {submit}
      </Button>
      <button type="button" className={LINK_BUTTON} onClick={onCancel}>
        {copy.cancel}
      </button>
    </div>
  );
}

/** Today as an ISO date on the browser's clock, for the year in the day labels. */
function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
