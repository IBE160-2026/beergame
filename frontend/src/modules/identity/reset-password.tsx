"use client";

import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";

import { checkPasswordReset, useConfirmPasswordReset } from "./api";
import { LoginForm } from "./login-form";
import { type NewPasswordError, tokenFromHash, validateNewPassword } from "./password-reset";

const copy = nb.auth.reset;
const INVALID = "reset_link_invalid";

/** The account e-mail of a usable link, or `null` for a link that is expired, used or unknown. */
async function checkLink(token: string): Promise<string | null> {
  if (!token) return null;
  try {
    return await checkPasswordReset(token);
  } catch (error) {
    if (error instanceof ApiRequestError && error.code === INVALID) return null;
    throw error;
  }
}

/**
 * «Nytt passord» (Story 3.6, UX-DR61). The token comes from the URL fragment. While the link is
 * checked the page shows the Skjelett. A link that is expired, used or unknown shows «Lenken er
 * utløpt eller brukt.» with «Send ny lenke»; a usable one the new-password form. After the save,
 * «Passordet er endret.» and «Logg inn» with the e-mail filled in.
 */
export function ResetPassword() {
  const [token, setToken] = useState<string>();
  const [done, setDone] = useState<string>();
  useEffect(() => setToken(tokenFromHash(window.location.hash)), []);

  const queryKey = ["auth", "password-reset", token ?? ""] as const;
  const link = useQuery({
    queryKey,
    queryFn: () => checkLink(token ?? ""),
    enabled: token !== undefined && done === undefined,
    retry: false,
    gcTime: 0,
  });
  const { phase, retry } = usePageState(
    { ...link, isPending: token === undefined || link.isPending },
    queryKey,
  );

  if (done !== undefined) return <ResetDone email={done} />;
  if (phase === "loading" || phase === "slow") {
    return (
      <div className="mt-6">
        <Skeleton heading={false} rows={2} />
        <LoadingNote visible={phase === "slow"} />
      </div>
    );
  }
  if (phase === "failed") {
    return (
      <div className="mt-6 flex flex-col gap-4">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button type="button" variant="secondary" onClick={retry} className="self-start">
          {nb.system.retry}
        </Button>
      </div>
    );
  }
  if (!link.data || !token) return <ResetInvalid />;
  return <NewPasswordForm token={token} email={link.data} onDone={setDone} onInvalid={() => link.refetch()} />;
}

function ResetInvalid() {
  return (
    <div className="mt-6 flex flex-col gap-3">
      <p className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body">{copy.invalid}</p>
      <p>
        <Link href="/glemt-passord" standalone>
          {copy.sendNew}
        </Link>
      </p>
    </div>
  );
}

function ResetDone({ email }: { email: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => ref.current?.focus(), []);
  return (
    <div className="mt-6">
      <p ref={ref} tabIndex={-1} className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body">
        {copy.done}
      </p>
      <h2 className="mt-8 text-headline text-ink">{nb.auth.login.title}</h2>
      <LoginForm defaultEmail={email} />
    </div>
  );
}

function NewPasswordForm({
  token,
  email,
  onDone,
  onInvalid,
}: {
  token: string;
  email: string;
  onDone: (email: string) => void;
  onInvalid: () => void;
}) {
  const action = useConfirmPasswordReset();
  const [error, setError] = useState<NewPasswordError>();
  const [submitted, setSubmitted] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);
  const [focusRequest, setFocusRequest] = useState(0);

  useEffect(() => {
    if (focusRequest) passwordRef.current?.focus();
  }, [focusRequest]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    const password = passwordRef.current?.value ?? "";
    const result = validateNewPassword(password);
    setError(result);
    setSubmitted(true);
    if (result) {
      setFocusRequest((n) => n + 1);
      return;
    }
    action.mutate(
      { token, password },
      {
        onSuccess: onDone,
        // The link stopped working meanwhile (used in another tab, or expired): show that state.
        onError: (failure) => {
          if (failure instanceof ApiRequestError && failure.code === INVALID) onInvalid();
        },
      },
    );
  }

  return (
    <>
      <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.lead(email)}</p>
      <form method="post" noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
        {/* For password managers: the account the new password belongs to. */}
        <input type="email" name="username" autoComplete="username" value={email} readOnly hidden />
        <TextField
          ref={passwordRef}
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          label={copy.password}
          hint={copy.passwordRule}
          error={error ? copy.errors[error] : undefined}
          onChange={() => {
            // After the first press a fixed error clears as it is typed, not on blur: a reason
            // vanishing on blur would move the button away from a press already under way.
            if (submitted) setError(validateNewPassword(passwordRef.current?.value ?? ""));
          }}
        />
        <ActionError message={action.errorMessage} />
        <Button type="submit" variant="primary" unavailable={action.isPending} className="mt-1 w-full">
          {copy.submit}
        </Button>
      </form>
    </>
  );
}
