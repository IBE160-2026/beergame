"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { clearDraft, loadDraft, saveDraft } from "@/lib/drafts";

import {
  answerReflection,
  currentQuestion,
  type Debrief,
  hasText,
  type Reflection,
  type ReflectionQuestion,
  reflectionDraftField,
  reflectionKey,
  useMyReflection,
  withAnswer,
} from "./api";

const copy = nb.debrief.reflection;
const LINE = "text-body-phone lg:text-body";
/** The api's longest answer, in characters. */
const MAX_LENGTH = 2000;

/**
 * The reflection questions between steps 3 and 4 (Story 9.6, FR-45, UX-DR31): shown under the
 * whole chain once the Explanation is saved; the api checks the gate. One question at a time, in
 * the order the api gives them (feelings, then evidence, then structure); the answered ones stay
 * above it as stored, read-only. What is typed is kept as a draft on this device per question
 * (`lib/drafts.ts`, AD-10) and is sent only by «Fortsett»; a failed save keeps the text. After a
 * save, focus moves to the next question's heading, or to the closing line. Each Student answers
 * on their own device and reads only their own answers (FR-43): the api keys them by the caller.
 */
export function ReflectionStep({ debrief, userId }: { debrief: Debrief; userId: string }) {
  const id = useId();
  const found = useMyReflection(debrief.id, true);
  const [moved, setMoved] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const reflection = found.data ?? null;
  // A question answered (here or on another device) keeps no unsent text on this device.
  const answeredIds = reflection?.questions.filter((q) => q.answer !== null).map((q) => q.id).join(" ") ?? "";
  useEffect(() => {
    for (const questionId of answeredIds.split(" ").filter(Boolean)) {
      clearDraft(userId, reflectionDraftField(debrief.class_session_id, questionId));
    }
  }, [answeredIds, userId, debrief.class_session_id]);
  if (found.isError && !reflection) {
    return (
      <section aria-label={copy.heading} data-debrief-reflection="failed" className="mt-10 border-t border-axis pt-4">
        <div className="flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void found.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  if (!reflection || reflection.questions.length === 0) return null;
  const current = currentQuestion(reflection);
  const answered = reflection.questions.filter((q) => q.answer !== null);
  return (
    <section aria-labelledby={`${id}-heading`} data-debrief-reflection="" className="mt-10 max-w-md border-t border-axis pt-4">
      <h2 id={`${id}-heading`} className="text-headline text-ink">
        {copy.heading}
      </h2>
      {/* Story 13.10 (FR-58): who reads the answers, and that those on feelings stay out of the
          Student report. */}
      <p data-reflection-report="" className={`${LINE} mt-2 text-ink-secondary`}>
        {copy.report}
      </p>
      {answered.length > 0 ? (
        <ol className="mt-4 flex flex-col gap-4">
          {answered.map((q) => (
            <li key={q.id} data-reflection-answered={q.id}>
              <p className={`${LINE} text-ink`}>{q.prompt}</p>
              <p className="mt-1 text-label text-ink-secondary">{copy.answered}</p>
              <p className={`${LINE} mt-1 border-l-2 border-axis pl-3 whitespace-pre-wrap text-ink`}>{q.answer!.text}</p>
            </li>
          ))}
        </ol>
      ) : null}
      {current ? (
        <Question
          key={current.id}
          debriefId={debrief.id}
          classSessionId={debrief.class_session_id}
          userId={userId}
          question={current}
          at={reflection.questions.indexOf(current) + 1}
          of={reflection.questions.length}
          focus={moved}
          notice={notice}
          onSaved={(elsewhere) => {
            setNotice(elsewhere ? copy.answeredElsewhere : null);
            setMoved(true);
          }}
          onOutOfOrder={() => {
            setNotice(copy.outOfOrder);
            setMoved(true);
          }}
        />
      ) : (
        <Done focus={moved} notice={notice} />
      )}
    </section>
  );
}

function Question({
  debriefId,
  classSessionId,
  userId,
  question,
  at,
  of,
  focus,
  notice,
  onSaved,
  onOutOfOrder,
}: {
  debriefId: string;
  classSessionId: string;
  userId: string;
  question: ReflectionQuestion;
  at: number;
  of: number;
  focus: boolean;
  notice: string | null;
  onSaved: (elsewhere: boolean) => void;
  onOutOfOrder: () => void;
}) {
  const id = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  const field = reflectionDraftField(classSessionId, question.id);
  const queryClient = useQueryClient();
  const [text, setText] = useState(() => loadDraft(userId, field) ?? "");
  const save = useAction({
    mutationFn: (typed: string) => answerReflection(debriefId, question.id, typed),
    fallback: copy.failed,
    onSuccess: (stored: ReflectionQuestion, typed: string) => {
      clearDraft(userId, field);
      // Answered on another device first: that answer stays, and the Student is told so.
      onSaved(stored.answer?.text !== typed);
      queryClient.setQueryData(reflectionKey(debriefId), (was: Reflection | undefined) =>
        was ? withAnswer(was, stored) : was,
      );
    },
  });
  // A new question after a save: focus moves to its heading, so the reading position is kept
  // (EXPERIENCE.md → Accessibility Floor). Never on the page's first view.
  useEffect(() => {
    if (focus) heading.current?.focus();
  }, [focus]);
  // Another device has answered further: the page reads where the answers stand.
  const code = save.isError ? errorCode(save.error) : null;
  const told = useRef(onOutOfOrder);
  useEffect(() => {
    told.current = onOutOfOrder;
  });
  useEffect(() => {
    if (code !== "reflection_out_of_order") return;
    told.current();
    void queryClient.invalidateQueries({ queryKey: reflectionKey(debriefId) });
  }, [code, queryClient, debriefId]);
  const empty = !hasText(text);
  const reasonId = `${id}-reason`;
  return (
    <form
      data-reflection-question={question.id}
      data-reflection-kind={question.kind}
      className="mt-6 flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (!empty && !save.isPending) save.mutate(text);
      }}
    >
      <h3 ref={heading} tabIndex={-1} className="text-label text-ink-secondary focus:outline-none">
        {copy.counter(at, of)}
      </h3>
      {notice ? (
        <p role="status" className={`${LINE} text-ink-secondary`}>
          {notice}
        </p>
      ) : null}
      {question.hint ? <p className={`${LINE} text-ink-secondary`}>{question.hint}</p> : null}
      <TextAreaField
        id={`${id}-text`}
        label={question.prompt}
        hint={copy.privacy}
        rows={5}
        maxLength={MAX_LENGTH}
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          saveDraft(userId, field, event.target.value);
          save.reset();
        }}
      />
      {empty ? (
        <p id={reasonId} data-reflection-reason="" className="text-body-phone text-ink-secondary">
          {copy.empty}
        </p>
      ) : null}
      <Button
        type="submit"
        variant="primary"
        unavailable={empty || save.isPending}
        aria-describedby={empty ? reasonId : undefined}
        className="w-full lg:w-auto lg:self-start"
      >
        {copy.next}
      </Button>
      <ActionError message={code === "reflection_out_of_order" ? undefined : save.errorMessage} />
    </form>
  );
}

function Done({ focus, notice }: { focus: boolean; notice: string | null }) {
  const line = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (focus) line.current?.focus();
  }, [focus]);
  return (
    <div className="mt-6 flex flex-col gap-2">
      {notice ? <p className={`${LINE} text-ink-secondary`}>{notice}</p> : null}
      <p ref={line} tabIndex={-1} role="status" data-reflection-done="" className={`${LINE} text-ink focus:outline-none`}>
        {copy.done}
      </p>
    </div>
  );
}
