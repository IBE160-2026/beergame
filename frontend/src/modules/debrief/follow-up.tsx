"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { errorCode, useAction } from "@/lib/api/mutation";
import { clearDraft, loadDraft, saveDraft } from "@/lib/drafts";

import { AiNote, DebriefText } from "./ai-text";
import {
  askFollowUp,
  type Debrief,
  type FollowUp as FollowUpData,
  type FollowUpAnswer,
  followUpDraftField,
  followUpKey,
  hasText,
  shownText,
  useMyFollowUp,
  waitMinutes,
  withFollowUp,
} from "./api";

const copy = nb.debrief.followUp;
const LINE = "text-body-phone lg:text-body";
/** The api's longest question, in characters. */
const MAX_LENGTH = 500;

/**
 * Follow-up questions about the Student's own Game (Story 9.15, FR-45, UX-DR31): under the
 * reflection questions once they are all answered, before step 4. Not shown at all when the api
 * says `off` (Debrief AI text off, no model, or a game played mostly by AI players); a line
 * replaces the field once it is `closed`. An answer is hints that point to where to look, as AI
 * text marked by `ai_generated` alone; a question outside the Game gets the fixed decline line,
 * never the KI's words. When no answer could be given, or too many were asked, the question stays
 * in the field. Each answer is announced politely and focus stays in the field (NFR-6). Nothing
 * here blocks a step: step 4 shows under it whatever happens.
 */
export function FollowUp({ debrief, userId }: { debrief: Debrief; userId: string }) {
  const id = useId();
  const found = useMyFollowUp(debrief.id, true);
  const followUp = found.data ?? null;
  if (found.isError && !followUp) {
    return (
      <section aria-labelledby={`${id}-heading`} data-debrief-follow-up="failed" className="mt-10 max-w-md border-t border-axis pt-4">
        <h2 id={`${id}-heading`} className="text-headline text-ink">
          {copy.heading}
        </h2>
        <div className="mt-4 flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void found.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  if (!followUp || followUp.state === "off") return null;
  return (
    <section
      aria-labelledby={`${id}-heading`}
      data-debrief-follow-up={followUp.state}
      className="mt-10 max-w-md border-t border-axis pt-4"
    >
      <h2 id={`${id}-heading`} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <p className={`${LINE} mt-2 text-ink-secondary`}>{copy.intro}</p>
      {followUp.asked.length > 0 ? (
        <ol className="mt-4 flex flex-col gap-4">
          {followUp.asked.map((each, index) => (
            <li key={`${each.asked_at ?? ""}-${index}`} data-follow-up-asked={each.outcome}>
              <p className="text-label text-ink-secondary">{copy.asked}</p>
              <p className={`${LINE} mt-1 border-l-2 border-axis pl-3 whitespace-pre-wrap text-ink`}>{each.question}</p>
              <Answer answer={each} />
            </li>
          ))}
        </ol>
      ) : null}
      {followUp.state === "closed" ? (
        <p data-follow-up-closed="" className={`${LINE} mt-6 text-ink`}>
          {copy.closed}
        </p>
      ) : (
        <Ask debrief={debrief} userId={userId} />
      )}
    </section>
  );
}

function Answer({ answer }: { answer: FollowUpAnswer }) {
  if (answer.outcome === "answered" && answer.answer) {
    return (
      <div data-follow-up-answer="">
        <p className={`${LINE} mt-2 text-ink`}>
          <DebriefText text={answer.answer} />
        </p>
        <AiNote text={answer.answer} className="mt-1" />
      </div>
    );
  }
  return (
    <p data-follow-up-answer="" className={`${LINE} mt-2 text-ink`}>
      {answer.outcome === "declined" ? copy.declined : copy.unanswered}
    </p>
  );
}

/** The text a screen reader hears for an answer (the visible list shows the same). */
function announcement(answer: FollowUpAnswer): string {
  if (answer.outcome === "answered" && answer.answer) return shownText(answer.answer);
  return answer.outcome === "declined" ? copy.declined : copy.unanswered;
}

function Ask({ debrief, userId }: { debrief: Debrief; userId: string }) {
  const id = useId();
  const field = followUpDraftField(debrief.class_session_id);
  const queryClient = useQueryClient();
  const textArea = useRef<HTMLTextAreaElement>(null);
  const [text, setText] = useState(() => loadDraft(userId, field) ?? "");
  const [heard, setHeard] = useState("");
  const [unanswered, setUnanswered] = useState(false);
  const ask = useAction({
    mutationFn: (question: string) => askFollowUp(debrief.id, question),
    fallback: copy.failed,
    onSuccess: (answer: FollowUpAnswer, asked: string) => {
      setHeard(announcement(answer));
      if (answer.outcome === "unanswered") {
        // No answer: the question stays in the field, to ask again or to go on.
        setUnanswered(true);
      } else {
        setUnanswered(false);
        // Text typed while the answer was on its way stays.
        setText((now) => (now === asked ? "" : now));
        if (text === asked) clearDraft(userId, field);
        queryClient.setQueryData(followUpKey(debrief.id), (was: FollowUpData | undefined) =>
          was ? withFollowUp(was, answer) : was,
        );
      }
      // The answer is announced; the Student stays in the field to ask the next one.
      textArea.current?.focus();
    },
  });
  const code = ask.isError ? errorCode(ask.error) : null;
  // Closed (the Individual test opened, the Testfrist passed) or switched off meanwhile: the
  // section reads the state again and the field gives way.
  useEffect(() => {
    if (code === "follow_up_closed" || code === "follow_up_off") {
      void queryClient.invalidateQueries({ queryKey: followUpKey(debrief.id) });
    }
  }, [code, queryClient, debrief.id]);
  const limited =
    code === "rate_limited" && ask.error instanceof ApiRequestError
      ? copy.rateLimited(waitMinutes(ask.error.fields.retry_after))
      : null;
  const empty = !hasText(text);
  const reasonId = `${id}-reason`;
  return (
    <form
      data-follow-up-form=""
      className="mt-6 flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (empty || ask.isPending) return;
        setHeard(copy.sending);
        setUnanswered(false);
        ask.mutate(text);
      }}
    >
      <TextAreaField
        ref={textArea}
        id={`${id}-text`}
        label={copy.label}
        hint={copy.privacy}
        rows={3}
        maxLength={MAX_LENGTH}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          saveDraft(userId, field, event.target.value);
          setUnanswered(false);
          // The wait after too many questions stays in view while the Student types.
          if (errorCode(ask.error) !== "rate_limited") ask.reset();
        }}
      />
      {empty ? (
        <p id={reasonId} data-follow-up-reason="" className="text-body-phone text-ink-secondary">
          {copy.empty}
        </p>
      ) : null}
      <Button
        type="submit"
        variant="primary"
        unavailable={empty || ask.isPending}
        aria-describedby={empty ? reasonId : undefined}
        className="w-full lg:w-auto lg:self-start"
      >
        {copy.send}
      </Button>
      {unanswered ? (
        <p data-follow-up-unanswered="" className={`${LINE} text-ink`}>
          {copy.unanswered}
        </p>
      ) : null}
      {limited ? (
        <p data-follow-up-limited="" className={`${LINE} text-ink`}>
          {limited}
        </p>
      ) : null}
      <ActionError message={code && code !== "rate_limited" && !code.startsWith("follow_up_") ? ask.errorMessage : undefined} />
      {/* The answer is read out politely, whatever it is; the list above shows it. */}
      <p role="status" className="sr-only" data-follow-up-status="">
        {limited ?? heard}
      </p>
    </form>
  );
}
