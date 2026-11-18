"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { NEXT_PARAM, safeReturnPath } from "@/lib/return-path";

import { useLogin } from "./api";
import { HOME_PATH, homeOf } from "./homes";
import { loginErrorMessage } from "./login-errors";
import { type LoginErrors, validateEmail, validateLogin, validatePassword } from "./validate-login";

const copy = nb.auth.login;

/**
 * The «Logg inn» form. It validates on the client first (Story 3.1), then logs in through the API
 * (Story 3.2). A refused login shows one line that never says which field was wrong; the input is
 * kept. After a login the User goes to `?neste=`, the validated page they came from (Story 3.4), or
 * else to their own home (Story 3.3). `defaultEmail` prefills the e-mail («Nytt passord», Story
 * 3.6).
 */
export function LoginForm({ defaultEmail }: { defaultEmail?: string } = {}) {
  const router = useRouter();
  const login = useLogin();
  const [errors, setErrors] = useState<LoginErrors>({});
  const [serverError, setServerError] = useState<string>();
  const [submitted, setSubmitted] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  // Which field to focus after a press. Focus moves after React has committed aria-invalid and
  // aria-describedby, so the screen reader reads the field together with its reason.
  const [focusRequest, setFocusRequest] = useState<{ field: "email" | "password"; n: number }>();

  useEffect(() => {
    if (!focusRequest) return;
    (focusRequest.field === "email" ? emailRef : passwordRef).current?.focus();
  }, [focusRequest]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (login.isPending) return;
    const email = emailRef.current?.value ?? "";
    const password = passwordRef.current?.value ?? "";
    const result = validateLogin({ email, password });
    setErrors(result);
    setSubmitted(true);
    setServerError(undefined);
    const field = result.email ? "email" : result.password ? "password" : undefined;
    if (field) {
      setFocusRequest((prev) => ({ field, n: (prev?.n ?? 0) + 1 }));
      return;
    }
    login.mutate(
      { email, password },
      {
        onSuccess: (user) => {
          const next = safeReturnPath(new URLSearchParams(window.location.search).get(NEXT_PARAM));
          router.push(next ?? HOME_PATH[homeOf(user)]);
        },
        onError: (error) => {
          const code = error instanceof ApiRequestError ? error.code : "unknown_error";
          setServerError(loginErrorMessage(code));
          setFocusRequest((prev) => ({ field: "email", n: (prev?.n ?? 0) + 1 }));
        },
      },
    );
  }

  // After the first press a field is checked again as it is typed, so a fixed error clears. Not on
  // blur: a reason vanishing on blur would move the button away from a press already under way.
  function onEmailChange() {
    if (submitted) setErrors((prev) => ({ ...prev, email: validateEmail(emailRef.current?.value ?? "") }));
  }
  function onPasswordChange() {
    if (submitted)
      setErrors((prev) => ({ ...prev, password: validatePassword(passwordRef.current?.value ?? "") }));
  }

  return (
    // method="post": a press before hydration must never put the password in the URL.
    <form method="post" noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
      <TextField
        ref={emailRef}
        id="email"
        name="email"
        type="email"
        inputMode="email"
        autoComplete="email"
        spellCheck={false}
        defaultValue={defaultEmail}
        label={copy.email}
        error={errors.email ? copy.errors[errors.email] : undefined}
        onChange={onEmailChange}
      />
      <TextField
        ref={passwordRef}
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        label={copy.password}
        error={errors.password ? copy.errors[errors.password] : undefined}
        onChange={onPasswordChange}
      />
      {serverError ? (
        <p role="alert" className="text-body-phone text-restordre">
          {serverError}
        </p>
      ) : null}
      <Button type="submit" variant="primary" unavailable={login.isPending} className="mt-1 w-full">
        {copy.submit}
      </Button>
      <p>
        <Link href="/glemt-passord" standalone>
          {copy.forgotPassword}
        </Link>
      </p>
    </form>
  );
}
