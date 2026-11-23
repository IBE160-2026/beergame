"use client";

import { useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";

import { type Consent, type ConsentDecision, useConsent, useDecideConsent } from "./api";

const copy = nb.homes.consent;

const DAY = new Intl.DateTimeFormat("nb-NO", { day: "numeric", month: "long", timeZone: "Europe/Oslo" });

/** «23. november»: the day a decision was taken, in Europe/Oslo. */
export function consentDay(iso: string): string {
  return DAY.format(new Date(iso));
}

/** The line a taken decision reads; null before one is taken. */
export function decisionLine(consent: Consent | undefined): string | null {
  if (!consent?.decision) return null;
  if (consent.decision === "given") return copy.given(consent.decided_at ? consentDay(consent.decided_at) : "");
  return copy.declined;
}

/**
 * A test student's consent on Hjem (Story 12.8, FR-82, AD-27, UX-DR57): before a decision, what
 * the Control test is for, what is stored and who the data controller is, then «Jeg samtykker» (the
 * page's primary action) and «Nei takk». A decline reads its line and offers «Jeg samtykker
 * likevel»; consent reads one line with its day. Each decision is stored with the text's version;
 * focus moves to the line that says what was stored.
 */
export function TestStudentConsent() {
  const found = useConsent(true);
  const decide = useDecideConsent();
  const lineRef = useRef<HTMLParagraphElement>(null);
  const [decided, setDecided] = useState(false);
  const consent = found.data;
  const line = decisionLine(consent);

  useEffect(() => {
    if (decided && line) lineRef.current?.focus();
  }, [decided, line]);

  if (found.isError && !consent) {
    return (
      <div className="mt-8 flex max-w-md flex-col items-start gap-3">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {copy.readFailed}
        </p>
        <Button onClick={() => void found.refetch()}>{nb.system.retry}</Button>
      </div>
    );
  }
  if (!consent) return null;
  const send = (decision: ConsentDecision) => {
    if (decide.isPending) return;
    decide.mutate(decision, { onSuccess: () => setDecided(true) });
  };

  if (consent.decision === "given") {
    return (
      <p
        ref={lineRef}
        tabIndex={-1}
        role="status"
        className="mt-8 max-w-md text-body-phone text-ink-secondary focus:outline-none lg:text-body"
      >
        {line}
      </p>
    );
  }
  return (
    <section aria-labelledby="test-student-consent" className="mt-8 max-w-md border-l-2 border-axis pl-4">
      <h2 id="test-student-consent" className="text-headline text-ink">
        {copy.title}
      </h2>
      {consent.decision === "declined" ? (
        <p
          ref={lineRef}
          tabIndex={-1}
          role="status"
          className="mt-2 text-body-phone text-ink focus:outline-none lg:text-body"
        >
          {line}
        </p>
      ) : (
        <div className="mt-2 flex flex-col gap-2 text-body-phone text-ink lg:text-body">
          <p>{copy.purpose}</p>
          <p>{copy.data}</p>
          <p>{copy.controller}</p>
          <p>{copy.seat}</p>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-3">
        <Button
          variant={consent.decision === "declined" ? "secondary" : "primary"}
          unavailable={decide.isPending}
          onClick={() => send("given")}
        >
          {consent.decision === "declined" ? copy.giveAfterAll : copy.give}
        </Button>
        {consent.decision === "declined" ? null : (
          <Button unavailable={decide.isPending} onClick={() => send("declined")}>
            {copy.decline}
          </Button>
        )}
      </div>
      <ActionError message={decide.errorMessage} className="mt-2" />
    </section>
  );
}
