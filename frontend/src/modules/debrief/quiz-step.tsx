"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { QuizChoice } from "@/components/quiz-choice";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";

import {
  DEBRIEF_STEPS,
  type Debrief,
  type Quiz,
  type QuizAttempt,
  quizAnswers,
  quizKey,
  type RenderedText,
  submitQuiz,
  useMyQuiz,
  useMySummary,
  withAttempt,
} from "./api";

const copy = nb.debrief.quiz;
const LINE = "text-body-phone lg:text-body";

/**
 * Step 5, the Debrief quiz (Story 9.9, FR-46, UX-DR37, EXPERIENCE.md → Quizvalg): shown once the
 * Debrief is finished, under «Debriefen er fullført». Each question is a Quizvalg; «Send svarene»
 * sends the choices, the api scores them by the answer key and answers the result, and focus moves
 * to its summary line. A wrong choice reads «Ditt svar, ikke riktig», the right one «Riktig»,
 * followed by the explanation from the api. «Prøv igjen» opens a new attempt (the order may
 * change) until every answer is right or the Testfrist has passed. The quiz counts toward nothing.
 */
export function QuizStep({ debrief }: { debrief: Debrief }) {
  const summary = useMySummary(debrief.id, true);
  const finished = Boolean(summary.data?.summary);
  const quiz = useMyQuiz(debrief.id, finished);
  const id = useId();
  const shown = Boolean(finished && quiz.data);
  // Stegene's Quiz link lands on `#debrief-quiz`, which renders only once the reads have answered:
  // scroll to it then, once.
  useEffect(() => {
    if (shown && window.location.hash === "#debrief-quiz") document.getElementById("debrief-quiz")?.scrollIntoView();
  }, [shown]);
  if (!finished) return null;
  const heading = (
    <h2 id={`${id}-heading`} className="text-headline text-ink">
      <span className="sr-only">{nb.debriefEntry.stepOf(5, DEBRIEF_STEPS)}: </span>
      <span aria-hidden="true" className="mr-3 tabular-nums">
        5
      </span>
      {copy.heading}
    </h2>
  );
  if (quiz.isError && !quiz.data) {
    return (
      <section id="debrief-quiz" aria-labelledby={`${id}-heading`} data-debrief-quiz="failed" className="mt-10 max-w-md border-t border-axis pt-4">
        {heading}
        <div className="mt-4 flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void quiz.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  return (
    <section id="debrief-quiz" aria-labelledby={`${id}-heading`} data-debrief-quiz="" className="mt-10 max-w-md scroll-mt-4 border-t border-axis pt-4">
      {heading}
      {quiz.data ? <Attempts debrief={debrief} quiz={quiz.data} /> : null}
    </section>
  );
}

function Attempts({ debrief, quiz }: { debrief: Debrief; quiz: Quiz }) {
  const queryClient = useQueryClient();
  const [retrying, setRetrying] = useState(false);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [missing, setMissing] = useState(false);
  // What to focus after the next render: the result's summary after a send, the new attempt's
  // first question after «Prøv igjen».
  const [focus, setFocus] = useState<"result" | "form" | null>(null);
  const result = useRef<HTMLParagraphElement>(null);
  const form = useRef<HTMLHeadingElement>(null);
  const send = useAction({
    mutationFn: async (answers: { question_id: string; choice_id: string }[]) => {
      try {
        return await submitQuiz(debrief.id, answers);
      } catch (error) {
        // Passed on another device: read the quiz again, so the passed result replaces the form.
        if (error instanceof ApiRequestError && error.code === "quiz_passed") {
          void queryClient.invalidateQueries({ queryKey: quizKey(debrief.id) });
        }
        throw error;
      }
    },
    messages: {
      test_deadline_passed: copy.deadlinePassed,
      quiz_passed: copy.alreadyPassed,
      validation_error: copy.unanswered,
    },
    fallback: copy.failed,
    onSuccess: (attempt: QuizAttempt) => {
      queryClient.setQueryData<Quiz>(quizKey(debrief.id), (old) => (old ? withAttempt(old, attempt) : old));
      // The next attempt's questions (their order may change) come with the refetch.
      void queryClient.invalidateQueries({ queryKey: quizKey(debrief.id) });
      setRetrying(false);
      setChosen({});
      setFocus("result");
    },
  });
  useEffect(() => {
    if (focus === "result") result.current?.focus();
    if (focus === "form") form.current?.focus();
    if (focus) setFocus(null);
  }, [focus]);

  const last = quiz.last;
  const showResult = last !== null && (last.passed || !retrying);
  return (
    <>
      <p className={`${LINE} mt-3 text-ink`}>{copy.intro}</p>
      {quiz.placeholder ? (
        <p data-quiz-placeholder="" className="mt-2 text-caption text-ink-secondary">
          {copy.placeholder}
        </p>
      ) : null}
      {showResult && last ? (
        <Result attempt={last} attempts={quiz.attempts} summaryRef={result}>
          {last.passed ? null : (
            <Button
              className="mt-6 w-full lg:w-auto"
              onClick={() => {
                send.reset();
                setRetrying(true);
                setFocus("form");
              }}
            >
              {copy.retry}
            </Button>
          )}
        </Result>
      ) : (
        <form
          data-quiz-form={quiz.attempts + 1}
          className="mt-6 flex flex-col gap-8"
          onSubmit={(event) => {
            event.preventDefault();
            if (send.isPending) return;
            const answers = quizAnswers(quiz.questions, chosen);
            setMissing(answers === null);
            if (answers) send.mutate(answers);
          }}
        >
          <h3 ref={form} tabIndex={-1} className="text-label text-ink-secondary focus:outline-none">
            {copy.attempt(quiz.attempts + 1)}
          </h3>
          {quiz.questions.map((question, i) => (
            <QuizChoice
              key={question.id}
              name={`quiz-${question.id}`}
              legend={
                <>
                  <span className="block text-label text-ink-secondary">{copy.questionOf(i + 1, quiz.questions.length)}</span>
                  {question.prompt}
                </>
              }
              options={question.choices}
              value={chosen[question.id] ?? null}
              onChange={(choice) => {
                setChosen((was) => ({ ...was, [question.id]: choice }));
                setMissing(false);
              }}
            />
          ))}
          <div className="flex flex-col gap-3">
            <Button type="submit" variant="primary" unavailable={send.isPending} className="w-full lg:w-auto lg:self-start">
              {copy.send}
            </Button>
            <ActionError message={missing ? copy.unanswered : send.errorMessage} />
          </div>
        </form>
      )}
    </>
  );
}

/** A scored attempt: the summary line (focused after a send), then each question as it was asked,
 * marked, with the explanation under a wrong one. */
function Result({
  attempt,
  attempts,
  summaryRef,
  children,
}: {
  attempt: QuizAttempt;
  attempts: number;
  summaryRef: React.RefObject<HTMLParagraphElement | null>;
  children?: React.ReactNode;
}) {
  return (
    <div data-quiz-result={attempt.number} data-quiz-passed={attempt.passed ? "" : undefined} className="mt-6">
      <p ref={summaryRef} tabIndex={-1} role="status" data-quiz-summary="" className={`${LINE} text-ink focus:outline-none`}>
        {copy.result(attempt.number, attempt.correct, attempt.asked)}{" "}
        {attempt.passed ? copy.passed(attempts) : copy.retryHint}
      </p>
      <div className="mt-6 flex flex-col gap-8">
        {attempt.results.map((each, i) => (
          <QuizChoice
            key={each.question_id}
            name={`quiz-result-${attempt.number}-${each.question_id}`}
            legend={
              <>
                <span className="block text-label text-ink-secondary">{copy.questionOf(i + 1, attempt.results.length)}</span>
                {each.prompt}
              </>
            }
            options={each.choices}
            value={each.chosen}
            marks={{ chosen: each.chosen, right: each.right_choice }}
          >
            {each.explanation ? (
              <p data-quiz-explanation="" className={`${LINE} mt-3 text-ink`}>
                <Text text={each.explanation} />
              </p>
            ) : null}
          </QuizChoice>
        ))}
      </div>
      {children}
    </div>
  );
}

/** Code-rendered text as written; AI text (Story 9.14) gets its prefix from `ai_generated` only. */
function Text({ text }: { text: RenderedText }) {
  return <>{text.ai_generated ? `${nb.debrief.aiPrefix} ${text.text}` : text.text}</>;
}
