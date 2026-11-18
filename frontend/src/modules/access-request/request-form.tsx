"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { api } from "@/lib/api/client";
import { request, useAction } from "@/lib/api/mutation";

import {
  type AccessRequestErrors,
  type AccessRequestFields,
  cleanAccessRequest,
  validateAccessRequest,
} from "./validate";

const copy = nb.accessRequest;
const FIELDS = ["name", "email", "institution"] as const;

/** Send a request for lecturer access (Story 3.13). The answer is the same for every address. */
function useRequestAccess() {
  return useAction<void, AccessRequestFields>({
    mutationFn: async (body) => {
      await request(() => api.POST("/api/auth/access-request", { body }));
    },
    messages: { rate_limited: copy.rateLimited },
    fallback: copy.failed,
  });
}

/**
 * «Be om lærertilgang» (Story 3.13, UX-DR61): Navn, E-post and Institusjon in one column and one
 * primary button. A field the api would refuse shows its reason and takes focus; nothing is sent.
 * After a taken request the form gives way to one line that takes focus: the Admin answers by
 * e-mail. A failure keeps what was typed, with the reason above the button.
 */
export function AccessRequestForm() {
  const action = useRequestAccess();
  const refs = {
    name: useRef<HTMLInputElement>(null),
    email: useRef<HTMLInputElement>(null),
    institution: useRef<HTMLInputElement>(null),
  };
  const [errors, setErrors] = useState<AccessRequestErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [sent, setSent] = useState(false);
  const sentRef = useRef<HTMLParagraphElement>(null);
  const [focus, setFocus] = useState<{ field: (typeof FIELDS)[number]; n: number }>();

  useEffect(() => {
    if (focus) refs[focus.field].current?.focus();
    // `refs` holds stable ref objects; only a new focus request moves focus.
  }, [focus]);
  useEffect(() => {
    if (sent) sentRef.current?.focus();
  }, [sent]);

  function values(): AccessRequestFields {
    return {
      name: refs.name.current?.value ?? "",
      email: refs.email.current?.value ?? "",
      institution: refs.institution.current?.value ?? "",
    };
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (action.isPending) return;
    const fields = values();
    const reasons = validateAccessRequest(fields);
    setErrors(reasons);
    setSubmitted(true);
    const first = FIELDS.find((field) => reasons[field]);
    if (first) {
      setFocus((prev) => ({ field: first, n: (prev?.n ?? 0) + 1 }));
      return;
    }
    action.mutate(cleanAccessRequest(fields), { onSuccess: () => setSent(true) });
  }

  if (sent) {
    return (
      <div className="mt-8 flex flex-col gap-5">
        <p
          ref={sentRef}
          tabIndex={-1}
          role="status"
          className="border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body"
        >
          {copy.sent}
        </p>
        <p>
          <Link href="/" standalone>
            {copy.toLanding}
          </Link>
        </p>
      </div>
    );
  }

  // After the first press a reason updates as it is typed, never on blur.
  const recheck = () => {
    if (submitted) setErrors(validateAccessRequest(values()));
  };

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="mt-8 flex flex-col gap-5">
      <TextField
        ref={refs.name}
        id="request-name"
        name="name"
        autoComplete="name"
        label={copy.name}
        error={errors.name}
        onChange={recheck}
      />
      <TextField
        ref={refs.email}
        id="request-email"
        name="email"
        type="email"
        inputMode="email"
        autoComplete="email"
        spellCheck={false}
        label={copy.email}
        error={errors.email}
        onChange={recheck}
      />
      <TextField
        ref={refs.institution}
        id="request-institution"
        name="institution"
        autoComplete="organization"
        label={copy.institution}
        error={errors.institution}
        onChange={recheck}
      />
      <ActionError message={action.errorMessage} />
      <Button type="submit" variant="primary" unavailable={action.isPending} className="mt-1 w-full">
        {copy.submit}
      </Button>
      <p>
        <Link href="/" standalone>
          {copy.toLanding}
        </Link>
      </p>
    </form>
  );
}
