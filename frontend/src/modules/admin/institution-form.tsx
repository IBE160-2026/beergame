"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { type Institution, useCreateInstitution } from "./api";
import { cleanName, nameError, refusalForField } from "./institutions";

const copy = nb.admin.institutions.create;

/**
 * «Ny Institusjon» (Story 3.11, FR-3): one Tekstfelt and the page's one primary button. A bad or
 * taken name shows the Tekstfelt's invalid state with the reason under it, and nothing is stored.
 * After the first press the reason follows what is typed, so a taken-name reason goes as soon as
 * the name changes. A created Institution empties the field, and its result line takes focus; the
 * line goes as soon as the field changes, or when a rename starts in the list (`otherStarted`
 * counts those starts; `onStart` tells the page that a create starts).
 */
export function InstitutionForm({ onStart, otherStarted = 0 }: { onStart?: () => void; otherStarted?: number } = {}) {
  const action = useCreateInstitution();
  const [error, setError] = useState<string>();
  const [submitted, setSubmitted] = useState(false);
  const [created, setCreated] = useState<Institution>();
  const nameRef = useRef<HTMLInputElement>(null);
  const createdRef = useRef<HTMLParagraphElement>(null);
  const [focusRequest, setFocusRequest] = useState(0);

  useEffect(() => {
    if (focusRequest) nameRef.current?.focus();
  }, [focusRequest]);
  useEffect(() => {
    if (created) createdRef.current?.focus();
  }, [created]);
  useEffect(() => {
    if (!otherStarted) return;
    setCreated(undefined);
    action.reset();
    // Only a new start elsewhere ends the line.
  }, [otherStarted]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    onStart?.();
    const value = nameRef.current?.value ?? "";
    const reason = nameError(value);
    setError(reason);
    setSubmitted(true);
    setCreated(undefined);
    action.reset();
    if (reason) {
      setFocusRequest((n) => n + 1);
      return;
    }
    action.mutate(cleanName(value), {
      onSuccess: (institution) => {
        if (nameRef.current) nameRef.current.value = "";
        setSubmitted(false);
        setCreated(institution);
      },
      onError: (failure) => {
        const field = refusalForField(failure);
        if (field) {
          setError(field);
          setFocusRequest((n) => n + 1);
        }
      },
    });
  }

  const general = action.isError && !refusalForField(action.error) ? copy.failed : undefined;

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-md flex-col gap-5">
      <TextField
        ref={nameRef}
        id="institution-name"
        name="name"
        autoComplete="off"
        label={copy.name}
        error={error}
        onChange={() => {
          setCreated(undefined);
          if (submitted) setError(nameError(nameRef.current?.value ?? ""));
        }}
      />
      <ActionError message={general} />
      <Button type="submit" variant="primary" unavailable={action.isPending} className="mt-1 w-full">
        {copy.submit}
      </Button>
      {created ? (
        <p
          ref={createdRef}
          tabIndex={-1}
          role="status"
          className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body"
        >
          {copy.created(created.name)}
        </p>
      ) : null}
    </form>
  );
}
