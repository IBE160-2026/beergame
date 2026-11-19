"use client";

import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, type Ref, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";

import {
  addRosterEntry,
  classesKey,
  classKey,
  invitationSummaryKey,
  type Registration,
  registerManually,
  registrationsKey,
  removeRosterEntry,
  rosterUploadKey,
  type UploadRow,
} from "./api";
import { clean } from "./classes";
import { useFormArea } from "./one-form";
import { type EntryErrors, entryRefusal, type EntryField, firstRefused, nameError } from "./roster-entry";

const copy = nb.classes.entries;

export const LINK_BUTTON =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

const PANEL = "flex w-full max-w-md flex-col items-start gap-4 rounded-sm border border-axis px-4 py-4";

/** Every query a change to the Roster moves: the Class (its count), the Lærerhjem, the staging
 * (a corrected row is gone), the counts and the status list. */
export function invalidateRoster(queryClient: QueryClient, classId: string) {
  for (const key of [
    classKey(classId),
    classesKey,
    rosterUploadKey(classId),
    invitationSummaryKey(classId),
    registrationsKey(classId),
  ]) {
    void queryClient.invalidateQueries({ queryKey: key, exact: true });
  }
}

/** Where «Registrer manuelt» was opened from: the address it prefills, the Roster row a changed
 * address replaces, or the staged invalid row it corrects. */
export type ManualFrom = { email: string; entryId?: string; uploadRow?: UploadRow };

/**
 * «Registrer manuelt» in place (Story 4.8, FR-9, UX-DR47): E-post (prefilled where the page has an
 * address), Navn, the primary «Registrer studenten» and «Avbryt». Focus moves to the first field
 * when it opens. A refused field shows its reason beside it, which clears as the Lecturer types.
 */
export function ManualForm({
  classId,
  from,
  idPrefix,
  onDone,
  onCancel,
}: {
  classId: string;
  from: ManualFrom;
  idPrefix: string;
  onDone: (result: Registration) => void;
  onCancel: () => void;
}) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(from.email);
  const [name, setName] = useState("");
  const [errors, setErrors] = useState<EntryErrors>({});
  const emailField = useRef<HTMLInputElement>(null);
  const nameField = useRef<HTMLInputElement>(null);
  const [focus, setFocus] = useState<{ field: EntryField; n: number }>({ field: "email", n: 0 });
  useEffect(() => (focus.field === "email" ? emailField : nameField).current?.focus(), [focus]);

  const action = useAction({
    mutationFn: () =>
      registerManually(classId, {
        email,
        name: clean(name),
        ...(from.entryId ? { roster_entry_id: from.entryId } : {}),
        ...(from.uploadRow ? { upload_row: from.uploadRow } : {}),
      }),
    fallback: copy.failed,
    onSuccess: (result) => {
      invalidateRoster(queryClient, classId);
      onDone(result);
    },
  });

  const refuse = (found: EntryErrors) => {
    setErrors(found);
    const first = firstRefused(found);
    if (first) setFocus((prev) => ({ field: first, n: prev.n + 1 }));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (action.isPending) return;
    action.reset();
    const nameLine = nameError(name);
    if (nameLine) {
      refuse({ name: nameLine });
      return;
    }
    action.mutate(undefined, { onError: (failure) => refuse(entryRefusal(failure)) });
  };

  return (
    <form noValidate aria-labelledby={`${idPrefix}-title`} className={PANEL} onSubmit={submit}>
      <h3 id={`${idPrefix}-title`} className="text-label text-ink">
        {copy.manualTitle}
      </h3>
      <p className="text-body-phone text-ink-secondary">{copy.manualLead}</p>
      <TextField
        id={`${idPrefix}-email`}
        ref={emailField}
        label={copy.email}
        type="email"
        inputMode="email"
        autoComplete="off"
        spellCheck={false}
        value={email}
        error={errors.email}
        onChange={(event) => {
          setEmail(event.target.value);
          setErrors((prev) => ({ ...prev, email: undefined }));
          if (action.isError) action.reset();
        }}
        className="w-full"
      />
      <TextField
        id={`${idPrefix}-name`}
        ref={nameField}
        label={copy.name}
        autoComplete="off"
        value={name}
        hint={copy.nameHint}
        error={errors.name}
        onChange={(event) => {
          setName(event.target.value);
          setErrors((prev) => ({ ...prev, name: undefined }));
          if (action.isError) action.reset();
        }}
        className="w-full"
      />
      <FormButtons
        submit={action.isPending ? copy.saving : copy.manualSubmit}
        pending={action.isPending}
        onCancel={() => {
          if (!action.isPending) onCancel();
        }}
      />
      <ActionError message={general(action.error, action.errorMessage)} />
    </form>
  );
}

/** «Legg til adresse» in place (Story 4.8, FR-7): one address, checked by the api as an upload's
 * are, with its reason beside the field. */
export function AddForm({
  classId,
  onDone,
  onCancel,
}: {
  classId: string;
  onDone: (result: Registration) => void;
  onCancel: () => void;
}) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string>();
  const field = useRef<HTMLInputElement>(null);
  const [focusField, setFocusField] = useState(0);
  useEffect(() => field.current?.focus(), [focusField]);
  const action = useAction({
    mutationFn: () => addRosterEntry(classId, email),
    fallback: copy.failed,
    onSuccess: (result) => {
      invalidateRoster(queryClient, classId);
      onDone(result);
    },
  });
  return (
    <form
      noValidate
      aria-labelledby="roster-add-title"
      className={PANEL}
      onSubmit={(event) => {
        event.preventDefault();
        if (action.isPending) return;
        action.reset();
        action.mutate(undefined, {
          onError: (failure) => {
            const found = entryRefusal(failure).email;
            if (found) {
              setError(found);
              setFocusField((n) => n + 1);
            }
          },
        });
      }}
    >
      <h3 id="roster-add-title" className="text-label text-ink">
        {copy.addTitle}
      </h3>
      <p className="text-body-phone text-ink-secondary">{copy.addLead}</p>
      <TextField
        id="roster-add-email"
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
      <FormButtons
        submit={action.isPending ? copy.saving : copy.addSubmit}
        pending={action.isPending}
        onCancel={() => {
          if (!action.isPending) onCancel();
        }}
      />
      <ActionError message={general(action.error, action.errorMessage)} />
    </form>
  );
}

/** «Fjern» in place (Story 4.8, FR-7): the consequence above the button, before it is pressed. */
export function RemoveConfirm({
  classId,
  item,
  onDone,
  onCancel,
}: {
  classId: string;
  item: Registration;
  /** With the result line: removed, or gone already (another tab removed it). */
  onDone: (text: string) => void;
  onCancel: () => void;
}) {
  const queryClient = useQueryClient();
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => button.current?.focus(), []);
  const action = useAction({
    mutationFn: () => removeRosterEntry(classId, item.id),
    fallback: copy.removeFailed,
    onSuccess: () => {
      invalidateRoster(queryClient, classId);
      onDone(copy.removed(item.email));
    },
  });
  const registered = item.status === "registered" || item.status === "registered_manually";
  const id = `remove-${item.id}`;
  return (
    <div role="group" aria-labelledby={`${id}-title`} className={PANEL}>
      <h4 id={`${id}-title`} className="text-label text-ink [overflow-wrap:anywhere]">
        {copy.removeTitle(item.email)}
      </h4>
      <p id={`${id}-consequence`} className="text-body-phone text-ink [overflow-wrap:anywhere]">
        {registered
          ? copy.removeRegistered(item.email)
          : item.status === "not_invited"
            ? copy.removeNotInvited(item.email)
            : copy.removeWaiting(item.email)}
      </p>
      <FormButtons
        ref={button}
        type="button"
        submit={action.isPending ? copy.saving : copy.removeSubmit}
        describedBy={`${id}-consequence`}
        pending={action.isPending}
        onSubmit={() => {
          if (action.isPending) return;
          action.mutate(undefined, {
            onError: (failure) => {
              // Gone already: say so in the result line, and the list shows what the api has now.
              if (errorCode(failure) === "not_found") {
                invalidateRoster(queryClient, classId);
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

function FormButtons({
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

/** A result line after one of these actions: read on focus, cleared when the next action starts. */
export function EntryResult({ text, ref }: { text: string; ref: Ref<HTMLParagraphElement> }) {
  return (
    <p
      ref={ref}
      tabIndex={-1}
      role="status"
      className="max-w-2xl text-body-phone text-ink [overflow-wrap:anywhere] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink lg:text-body"
    >
      {text}
    </p>
  );
}

/** The form's general line: none when the api named the refused field, which says why beside it. */
function general(error: unknown, message: string | undefined): string | undefined {
  return firstRefused(entryRefusal(error)) ? undefined : message;
}

/** The result line of an added or manually registered address. */
export function resultText(kind: "add" | "manual", result: Registration): string {
  if (kind === "manual") return copy.registered(result.email);
  return result.status === "not_invited" ? copy.added(result.email) : copy.restored(result.email);
}

/**
 * Under «Klasseliste»: the Lenker «Legg til adresse» and «Registrer manuelt», each opening its
 * form in place (one at a time), and the result line of the last one. «Avbryt» returns focus to
 * the Lenke that opened the form.
 */
export function RosterEntryActions({ classId }: { classId: string }) {
  const [open, setOpen] = useState<"add" | "manual" | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const openers = { add: useRef<HTMLButtonElement>(null), manual: useRef<HTMLButtonElement>(null) };
  const resultLine = useRef<HTMLParagraphElement>(null);
  const [focusNext, setFocusNext] = useState<"add" | "manual" | "result" | null>(null);
  useEffect(() => {
    if (!focusNext) return;
    const target = focusNext === "result" ? resultLine.current : openers[focusNext].current;
    target?.focus();
    setFocusNext(null);
  });

  // Another area's form closes this one and clears its result line (one form on the page).
  const take = useFormArea("entries", () => {
    setOpen(null);
    setResult(null);
  });
  const start = (which: "add" | "manual") => {
    setResult(null); // a new action clears the last result line
    setOpen(which);
    take();
  };
  const cancel = (which: "add" | "manual") => {
    setOpen(null);
    setFocusNext(which);
  };
  const done = (which: "add" | "manual", registration: Registration) => {
    setOpen(null);
    setResult(resultText(which, registration));
    setFocusNext("result");
  };

  return (
    <div className="flex flex-col items-start gap-4">
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        <button
          ref={openers.add}
          type="button"
          className={LINK_BUTTON}
          aria-expanded={open === "add"}
          onClick={() => start("add")}
        >
          {copy.add}
        </button>
        <button
          ref={openers.manual}
          type="button"
          className={LINK_BUTTON}
          aria-expanded={open === "manual"}
          onClick={() => start("manual")}
        >
          {copy.manual}
        </button>
      </div>
      {open === "add" ? (
        <AddForm classId={classId} onDone={(r) => done("add", r)} onCancel={() => cancel("add")} />
      ) : null}
      {open === "manual" ? (
        <ManualForm
          classId={classId}
          from={{ email: "" }}
          idPrefix="roster-manual"
          onDone={(r) => done("manual", r)}
          onCancel={() => cancel("manual")}
        />
      ) : null}
      {result ? <EntryResult text={result} ref={resultLine} /> : null}
    </div>
  );
}
