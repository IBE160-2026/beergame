"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SegmentedChoice } from "@/components/segmented-choice";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { errorCode } from "@/lib/api/mutation";
import { validateEmail } from "@/modules/identity/validate-login";

import { type AccessRequest, type AccountRole, type SentInvitation, useSendInvitation } from "./api";

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

/** The reason beside the e-mail field for a refused send, or undefined when the refusal is not
 * about the address (the general line then says it). */
export function inviteRefusalForField(error: unknown): string | undefined {
  return errorCode(error) === "account_deactivated" ? copy.errors.accountDeactivated : undefined;
}

/** A press of «Inviter … som Faglærer» on a request for lecturer access; `n` counts presses. */
export type InvitePrefill = { request: AccessRequest; n: number };

/** The result line of a sent Invitation, with the address, the role and its real days. */
export function sentLine(sent: SentInvitation): string {
  return copy.sent(sent.email, copy.roles[sent.role], sent.valid_days);
}

/**
 * «Inviter» on «Brukere og roller» (Story 3.7, FR-1): e-post, Rolle and one primary button,
 * in one column. A bad address shows the Tekstfelt's invalid state and nothing is sent. After a
 * sent Invitation the result line takes focus and the field is emptied for the next one; the
 * role stays as chosen.
 *
 * «Inviter … som Faglærer» on a request for lecturer access (Story 3.13) passes `prefill`: the
 * form takes the address and the role Faglærer, says which request it was filled from, and the
 * e-mail field takes focus. Nothing is sent until «Send Invitasjon»; the Invitation then closes
 * the request.
 */
export function InviteForm({ prefill }: { prefill?: InvitePrefill }) {
  const action = useSendInvitation();
  const [role, setRole] = useState<AccountRole>("lecturer");
  const [error, setError] = useState<string>();
  const [submitted, setSubmitted] = useState(false);
  const [sent, setSent] = useState<SentInvitation>();
  const emailRef = useRef<HTMLInputElement>(null);
  const sentRef = useRef<HTMLParagraphElement>(null);
  const [focusRequest, setFocusRequest] = useState(0);
  const [from, setFrom] = useState<AccessRequest>();

  useEffect(() => {
    if (!prefill || !emailRef.current) return;
    emailRef.current.value = prefill.request.email;
    setRole("lecturer");
    setFrom(prefill.request);
    setError(undefined);
    setSubmitted(false);
    setSent(undefined);
    action.reset();
    emailRef.current.scrollIntoView?.({ block: "center" });
    emailRef.current.focus();
    // Only a new press of «Inviter» fills the form again.
  }, [prefill]);

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
      { email: email.trim(), role, ...(from ? { access_request_id: from.id } : {}) },
      {
        onSuccess: (invitation) => {
          if (emailRef.current) emailRef.current.value = "";
          setSubmitted(false);
          setFrom(undefined);
          setSent(invitation);
        },
        onError: (failure) => {
          const field = inviteRefusalForField(failure);
          if (field) {
            setError(field);
            setFocusRequest((n) => n + 1);
          }
        },
      },
    );
  }

  // A refusal about the address stands beside the field, not as the general line.
  const general = action.isError && !inviteRefusalForField(action.error) ? action.errorMessage : undefined;

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="flex max-w-md flex-col gap-5">
      {from ? (
        <p role="status" className="text-body-phone text-ink-secondary lg:text-body [overflow-wrap:anywhere]">
          {copy.fromRequest(from.name)}
        </p>
      ) : null}
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
          // Another address no longer answers the request the form was filled from (Story 3.13).
          if (from && emailRef.current?.value.trim().toLowerCase() !== from.email) setFrom(undefined);
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
          // Only a Faglærer Invitation answers a request for lecturer access (Story 3.13).
          if (next !== "lecturer") setFrom(undefined);
          setRole(next);
        }}
      />
      <ActionError message={general} />
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
