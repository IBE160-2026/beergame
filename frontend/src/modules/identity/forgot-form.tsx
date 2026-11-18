"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { useRequestPasswordReset } from "./api";
import { type EmailError, validateEmail } from "./validate-login";

const copy = nb.auth.forgot;

/**
 * The «Glemt passord» form (Story 3.6). After any accepted request it shows the same line,
 * whether or not the address has an account (UX-DR61); the line takes focus so it is read.
 */
export function ForgotForm() {
  const action = useRequestPasswordReset();
  const [error, setError] = useState<EmailError>();
  const [submitted, setSubmitted] = useState(false);
  const [sent, setSent] = useState(false);
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
    const result = validateEmail(email);
    setError(result);
    setSubmitted(true);
    if (result) {
      setFocusRequest((n) => n + 1);
      return;
    }
    action.mutate({ email: email.trim() }, { onSuccess: () => setSent(true) });
  }

  if (sent) {
    return (
      <div className="mt-8 flex flex-col gap-5">
        <p ref={sentRef} tabIndex={-1} className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body">
          {copy.sent}
        </p>
        <p>
          <Link href="/logg-inn" standalone>
            {nb.navigation.toLogin}
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
      <TextField
        ref={emailRef}
        id="email"
        name="email"
        type="email"
        inputMode="email"
        autoComplete="email"
        spellCheck={false}
        label={copy.email}
        error={error ? nb.auth.login.errors[error] : undefined}
        onChange={() => {
          // After the first press a fixed error clears as it is typed, not on blur: a reason
          // vanishing on blur would move the button away from a press already under way.
          if (submitted) setError(validateEmail(emailRef.current?.value ?? ""));
        }}
      />
      <ActionError message={action.errorMessage} />
      <Button type="submit" variant="primary" unavailable={action.isPending} className="mt-1 w-full">
        {copy.submit}
      </Button>
      <p>
        <Link href="/logg-inn" standalone>
          {nb.navigation.toLogin}
        </Link>
      </p>
    </form>
  );
}
