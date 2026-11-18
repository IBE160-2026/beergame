"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";

import { type LoginErrors, validateEmail, validateLogin, validatePassword } from "./validate-login";

const copy = nb.auth.login;

/**
 * The «Logg inn» form. In Story 3.1 it validates on the client and sends nothing. Story 3.2
 * connects it to the API.
 */
export function LoginForm() {
  const [errors, setErrors] = useState<LoginErrors>({});
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
    const result = validateLogin({
      email: emailRef.current?.value ?? "",
      password: passwordRef.current?.value ?? "",
    });
    setErrors(result);
    setSubmitted(true);
    const field = result.email ? "email" : result.password ? "password" : undefined;
    if (field) setFocusRequest((prev) => ({ field, n: (prev?.n ?? 0) + 1 }));
    // Valid input: the login request comes in Story 3.2. Nothing is sent here.
  }

  // After the first press, a field is checked again when it is left, so a fixed error clears.
  function onEmailBlur() {
    if (submitted) setErrors((prev) => ({ ...prev, email: validateEmail(emailRef.current?.value ?? "") }));
  }
  function onPasswordBlur() {
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
        label={copy.email}
        error={errors.email ? copy.errors[errors.email] : undefined}
        onBlur={onEmailBlur}
      />
      <TextField
        ref={passwordRef}
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        label={copy.password}
        error={errors.password ? copy.errors[errors.password] : undefined}
        onBlur={onPasswordBlur}
      />
      <Button type="submit" variant="primary" className="mt-1 w-full">
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
