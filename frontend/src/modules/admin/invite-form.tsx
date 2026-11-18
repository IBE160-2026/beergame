"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SegmentedChoice } from "@/components/segmented-choice";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { validateEmail } from "@/modules/identity/validate-login";

import { type AccountRole, type SentInvitation, useSendInvitation } from "./api";

const copy = nb.admin.users.invite;

const ROLES: readonly { value: AccountRole; label: string }[] = [
  { value: "lecturer", label: copy.roles.lecturer },
  { value: "admin", label: copy.roles.admin },
];

/** The reason beside the e-mail field, or undefined for an address the server will take. The
 * empty field has its own line here, since «Skriv e-postadressen din.» speaks to the account
 * holder. */
export function inviteEmailError(value: string): string | undefined {
  const error = validateEmail(value);
  if (!error) return undefined;
  return error === "emailEmpty" ? copy.errors.emailEmpty : nb.auth.login.errors[error];
}

/** The result line of a sent Invitation, with the address, the role and its real days. */
export function sentLine(sent: SentInvitation): string {
  return copy.sent(sent.email, copy.roles[sent.role], sent.valid_days);
}

/**
 * «Inviter» on «Brukere og roller» (Story 3.7, FR-1): e-post, Rolle and one primary button,
 * in one column. A bad address shows the Tekstfelt's invalid state and nothing is sent. After a
 * sent Invitation the result line takes focus and the field is emptied for the next one; the
 * role stays as chosen.
 */
export function InviteForm() {
  const action = useSendInvitation();
  const [role, setRole] = useState<AccountRole>("lecturer");
  const [error, setError] = useState<string>();
  const [submitted, setSubmitted] = useState(false);
  const [sent, setSent] = useState<SentInvitation>();
  const emailRef = useRef<HTMLInputElement>(null);
  const sentRef = useRef<HTMLParagraphElement>(null);
  const [focusRequest, setFocusRequest] = useState(0);

  useEffect(() => {
    if (focusRequest) emailRef.current?.focus();
  }, [focusRequest]);
  useEffect(() => {
    if (sent) sentRef.current?.focus();
  }, [sent]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    const email = emailRef.current?.value ?? "";
    const reason = inviteEmailError(email);
    setError(reason);
    setSubmitted(true);
    // A new press ends the earlier result line, so it never stands beside a new reason.
    setSent(undefined);
    if (reason) {
      setFocusRequest((n) => n + 1);
      return;
    }
    action.mutate(
      { email: email.trim(), role },
      {
        onSuccess: (invitation) => {
          if (emailRef.current) emailRef.current.value = "";
          setSubmitted(false);
          setSent(invitation);
        },
      },
    );
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-md flex-col gap-5">
      <TextField
        ref={emailRef}
        id="invite-email"
        name="email"
        type="email"
        inputMode="email"
        autoComplete="off"
        spellCheck={false}
        label={copy.email}
        error={error}
        onChange={() => {
          // The result line speaks of the last send; it goes as soon as the form changes.
          setSent(undefined);
          // After the first press a reason updates as it is typed, never on blur: a reason
          // vanishing on blur would move the button away from a press already under way.
          if (submitted) setError(inviteEmailError(emailRef.current?.value ?? ""));
        }}
      />
      <SegmentedChoice
        name="role"
        legend={copy.role}
        options={ROLES}
        value={role}
        onChange={(next) => {
          setSent(undefined);
          setRole(next);
        }}
      />
      <ActionError message={action.errorMessage} />
      <Button type="submit" variant="primary" unavailable={action.isPending} className="mt-1 w-full">
        {copy.submit}
      </Button>
      {sent ? (
        <p
          ref={sentRef}
          tabIndex={-1}
          className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body"
        >
          {sentLine(sent)}
        </p>
      ) : null}
    </form>
  );
}
