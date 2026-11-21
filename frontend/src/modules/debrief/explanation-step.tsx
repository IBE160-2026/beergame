"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { NetOverGameChart } from "@/components/net-over-game-chart";
import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { clearDraft, loadDraft, saveDraft } from "@/lib/drafts";

import {
  type Debrief,
  type Explanation,
  explanationDraftField,
  explanationKey,
  hasText,
  myDebriefKey,
  sendExplanation,
  useMyExplanation,
  useNetInventory,
} from "./api";

const copy = nb.debriefEntry.explanation;
const LINE = "text-body-phone lg:text-body";
/** The api's longest Explanation, in characters. */
const MAX_LENGTH = 5000;

/**
 * Debrief step 1 «Skriv Forklaringen først» (Story 9.3, FR-41, UX-DR31, `07-debrief.png`): the
 * Student's own «Ditt netto lager, hele spillet» with «Vis som tabell», then «Hvorfor svingte
 * lageret ditt?» and «Send Forklaring». What is typed is kept as a draft on this device
 * (`lib/drafts.ts`, AD-10) and is sent only by the press; a failed send keeps the text. Once sent,
 * the Explanation shows as it was stored, read-only: it is never changed (FR-41). Every number
 * comes from the api.
 */
export function ExplanationStep({ debrief, userId }: { debrief: Debrief; userId: string }) {
  const net = useNetInventory(debrief.id);
  const mine = useMyExplanation(debrief.id);
  const [existed, setExisted] = useState(false);
  const [justSent, setJustSent] = useState(false);
  const stored = mine.data?.explanation ?? null;
  // A failed read says so and can be tried again; the form never stands in for an Explanation
  // that could not be read (it may be sent already).
  const failed = net.isError || mine.isError;
  return (
    <div className="mt-4 flex flex-col gap-6">
      {net.data ? <NetOverGameChart weeks={net.data.weeks} /> : null}
      {failed ? (
        <div data-step-failed="" className="flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button
            onClick={() => {
              if (net.isError) void net.refetch();
              if (mine.isError) void mine.refetch();
            }}
          >
            {nb.system.retry}
          </Button>
        </div>
      ) : null}
      {mine.isPending || mine.isError ? null : stored ? (
        <Sent explanation={stored} existed={existed} focus={justSent || existed} />
      ) : (
        <Write
          debriefId={debrief.id}
          classSessionId={debrief.class_session_id}
          userId={userId}
          onSent={() => setJustSent(true)}
          onExisted={() => setExisted(true)}
        />
      )}
    </div>
  );
}

function Write({
  debriefId,
  classSessionId,
  userId,
  onSent,
  onExisted,
}: {
  debriefId: string;
  classSessionId: string;
  userId: string;
  onSent: () => void;
  onExisted: () => void;
}) {
  const id = useId();
  const field = explanationDraftField(classSessionId);
  const queryClient = useQueryClient();
  const [text, setText] = useState(() => loadDraft(userId, field) ?? "");
  const send = useAction({
    mutationFn: (typed: string) => sendExplanation(debriefId, typed),
    fallback: copy.failed,
    onSuccess: (saved: Explanation) => {
      clearDraft(userId, field);
      onSent();
      queryClient.setQueryData(explanationKey(debriefId), { explanation: saved });
      // Story 9.11: in a Group debrief this Explanation may move the shared step on.
      void queryClient.invalidateQueries({ queryKey: myDebriefKey(classSessionId) });
    },
  });
  // Sent from another device already: the stored one is shown and this draft has no use.
  const code = send.isError ? errorCode(send.error) : null;
  const told = useRef(onExisted);
  useEffect(() => {
    told.current = onExisted;
  });
  useEffect(() => {
    if (code !== "explanation_exists") return;
    clearDraft(userId, field);
    told.current();
    void queryClient.invalidateQueries({ queryKey: explanationKey(debriefId) });
  }, [code, userId, field, queryClient, debriefId]);
  const empty = !hasText(text);
  const reasonId = `${id}-reason`;
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!empty && !send.isPending) send.mutate(text);
      }}
    >
      <TextAreaField
        id={`${id}-text`}
        label={copy.prompt}
        hint={copy.hint}
        rows={6}
        maxLength={MAX_LENGTH}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          saveDraft(userId, field, event.target.value);
          send.reset();
        }}
      />
      {empty ? (
        <p id={reasonId} data-explanation-reason="" className="text-body-phone text-ink-secondary">
          {copy.empty}
        </p>
      ) : null}
      <Button
        type="submit"
        variant="primary"
        unavailable={empty || send.isPending}
        aria-describedby={empty ? reasonId : undefined}
        className="w-full lg:w-auto lg:self-start"
      >
        {copy.send}
      </Button>
      {/* Sent already from elsewhere: the stored one replaces the form once it is read again. */}
      <ActionError message={code === "explanation_exists" ? copy.exists : send.errorMessage} />
    </form>
  );
}

function Sent({ explanation, existed, focus }: { explanation: Explanation; existed: boolean; focus: boolean }) {
  const heading = useRef<HTMLHeadingElement>(null);
  // After a send the form is gone: focus moves to what took its place, so the reading position
  // is kept (EXPERIENCE.md → Accessibility Floor).
  useEffect(() => {
    if (focus) heading.current?.focus();
  }, [focus]);
  return (
    <section aria-labelledby="debrief-explanation" data-explanation-sent="">
      <h3 id="debrief-explanation" ref={heading} tabIndex={-1} className="text-label text-ink focus:outline-none">
        {copy.sentTitle}
      </h3>
      <p className={`${LINE} mt-2 border-l-2 border-axis pl-3 whitespace-pre-wrap text-ink`}>{explanation.text}</p>
      <p role="status" className={`${LINE} mt-3 text-ink-secondary`}>
        {existed ? copy.exists : copy.sent}
      </p>
    </section>
  );
}
