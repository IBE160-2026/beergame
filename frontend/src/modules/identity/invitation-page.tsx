"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";

import { type CheckedInvitation, checkInvitation, useAcceptInvitation, useRequestInvitationRenewal } from "./api";
import { HOME_PATH, homeOf } from "./homes";
import {
  invitationLead,
  type InvitationErrors,
  normaliseName,
  validateInvitation,
  validateName,
  validityLine,
} from "./invitation";
import { tokenFromHash, validateNewPassword } from "./password-reset";

const copy = nb.auth.invitation;
const INVALID = "invitation_link_invalid";

/** The Invitation of a usable link, or `null` for one that is expired, used or unknown. */
async function checkLink(token: string): Promise<CheckedInvitation | null> {
  if (!token) return null;
  try {
    return await checkInvitation(token);
  } catch (error) {
    if (error instanceof ApiRequestError && error.code === INVALID) return null;
    throw error;
  }
}

/**
 * «Du er invitert» (Story 3.8, FR-1, FR-4, UX-DR61). The token comes from the URL fragment. While
 * the link is checked the page shows the Skjelett. A usable link shows the new-account form, or,
 * when the address already has an account, a login that adds the role. A Student Invitation (Story
 * 4.5) names its Class and Lecturer instead of a role, and joins the account to the Class. Either way the User then
 * lands on their own home. A link that is expired or used offers one action: ask for a new one.
 */
export function InvitationPage() {
  const [token, setToken] = useState<string>();
  useEffect(() => setToken(tokenFromHash(window.location.hash)), []);

  const queryKey = ["auth", "invitation", token ?? ""] as const;
  const link = useQuery({
    queryKey,
    queryFn: () => checkLink(token ?? ""),
    enabled: token !== undefined,
    retry: false,
    gcTime: 0,
  });
  const { phase, retry } = usePageState({ ...link, isPending: token === undefined || link.isPending }, queryKey);

  if (phase === "loading" || phase === "slow") {
    return (
      <div className="mt-6">
        <Skeleton heading={false} rows={3} />
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
  if (!link.data || !token) return <InvitationInvalid token={token ?? ""} />;
  return (
    <AcceptForm
      // A new form when the link's state changes (an account appeared meanwhile).
      key={String(link.data.has_account)}
      token={token}
      invitation={link.data}
      onStale={() => link.refetch()}
    />
  );
}

function InvitationInvalid({ token }: { token: string }) {
  const action = useRequestInvitationRenewal();
  const doneRef = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (action.isSuccess) doneRef.current?.focus();
  }, [action.isSuccess]);

  // The result line replaces the state it answers, as every result line does (EXPERIENCE.md),
  // so two ruled lines never stack.
  if (action.isSuccess) {
    return (
      <div className="mt-6">
        <p ref={doneRef} tabIndex={-1} className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body">
          {copy.requested}
        </p>
      </div>
    );
  }
  return (
    <div className="mt-6 flex flex-col gap-4">
      <p className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body">{copy.invalid}</p>
      <ActionError message={action.errorMessage} />
      <Button
        type="button"
        variant="secondary"
        unavailable={action.isPending}
        onClick={() => {
          if (!action.isPending) action.mutate({ token });
        }}
        className="self-start"
      >
        {copy.requestNew}
      </Button>
    </div>
  );
}

function AcceptForm({
  token,
  invitation,
  onStale,
}: {
  token: string;
  invitation: CheckedInvitation;
  onStale: () => void;
}) {
  const router = useRouter();
  const existing = invitation.has_account;
  const student = invitation.kind === "student";
  const action = useAcceptInvitation(existing, student);
  const [errors, setErrors] = useState<InvitationErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const [focusRequest, setFocusRequest] = useState<{ field: "name" | "password"; n: number }>();

  useEffect(() => {
    if (!focusRequest) return;
    (focusRequest.field === "name" ? nameRef : passwordRef).current?.focus();
  }, [focusRequest]);

  function check(name: string, password: string): InvitationErrors {
    if (!existing) return validateInvitation(name, password);
    return { password: password === "" ? "passwordEmpty" : undefined };
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    const name = nameRef.current?.value ?? "";
    const password = passwordRef.current?.value ?? "";
    const result = check(name, password);
    setErrors(result);
    setSubmitted(true);
    const field = result.name ? "name" : result.password ? "password" : undefined;
    if (field) {
      setFocusRequest((prev) => ({ field, n: (prev?.n ?? 0) + 1 }));
      return;
    }
    action.mutate(
      { token, name: normaliseName(name), password },
      {
        onSuccess: (user) => router.push(HOME_PATH[homeOf(user)]),
        onError: (failure) => {
          // The link stopped working, or an account was made meanwhile: show that state.
          const code = failure instanceof ApiRequestError ? failure.code : "";
          if (code === INVALID || code === "account_exists") onStale();
        },
      },
    );
  }

  // After the first press a reason updates as it is typed, never on blur: a reason vanishing on
  // blur would move the button away from a press already under way.
  function onNameChange() {
    if (submitted) setErrors((prev) => ({ ...prev, name: validateName(nameRef.current?.value ?? "") }));
  }
  function onPasswordChange() {
    if (!submitted) return;
    const password = passwordRef.current?.value ?? "";
    setErrors((prev) => ({
      ...prev,
      password: existing ? (password === "" ? "passwordEmpty" : undefined) : validateNewPassword(password),
    }));
  }

  const passwordErrors = existing ? nb.auth.login.errors : copy.errors;
  return (
    <>
      <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">
        {invitationLead(invitation, existing)}
      </p>
      <form method="post" noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
        {existing ? null : (
          <TextField
            ref={nameRef}
            id="name"
            name="name"
            autoComplete="name"
            label={copy.name}
            error={errors.name ? copy.errors[errors.name] : undefined}
            onChange={onNameChange}
          />
        )}
        <TextField
          id="email"
          name="username"
          type="email"
          autoComplete="username"
          label={existing ? copy.existing.email : student ? copy.student.email : copy.email}
          value={invitation.email}
          readOnly
        />
        <TextField
          ref={passwordRef}
          id="password"
          name="password"
          type="password"
          autoComplete={existing ? "current-password" : "new-password"}
          label={existing ? copy.existing.password : copy.password}
          hint={existing ? undefined : copy.passwordRule}
          error={
            errors.password === "passwordEmpty"
              ? passwordErrors.passwordEmpty
              : errors.password
                ? copy.errors[errors.password]
                : undefined
          }
          onChange={onPasswordChange}
        />
        <ActionError message={action.errorMessage} />
        <Button type="submit" variant="primary" unavailable={action.isPending} className="mt-1 w-full">
          {existing ? (student ? copy.student.existing.submit : copy.existing.submit) : copy.submit}
        </Button>
        <p className="text-body-phone text-ink-secondary lg:text-body">{validityLine(invitation.valid_days, student)}</p>
        {existing ? (
          <p>
            <Link href="/glemt-passord" standalone>
              {nb.auth.login.forgotPassword}
            </Link>
          </p>
        ) : null}
      </form>
    </>
  );
}
