"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Switch } from "@/components/switch";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";

import { answerText, excludedIds, type SessionQuiz, saveQuizExclusions, sessionQuizKey, useSessionQuiz } from "./api";

const copy = nb.debrief.quizExclusions;
const LINE = "text-body-phone lg:text-body";

/**
 * The Klasseøkt's «Debrief-quiz» block (Story 9.10, FR-46, UX-DR12, AD-12): the Class session's
 * quiz, each question with its choices and answer key. An owner takes a question out with a Bryter
 * per question; like every Klasseøkt choice it takes effect only on a save, here the block's own
 * secondary «Lagre quizvalg», because exclusions stay open after the lock until the Test deadline,
 * when «Lagre Klasseøkt» no longer exists. Help text states the scope. An Assistant lecturer, an
 * archived Class or a passed Test deadline reads the state as text. Nothing renders for a User the
 * api refuses.
 */
export function QuizExclusionsBlock({ classSessionId }: { classSessionId: string }) {
  const found = useSessionQuiz(classSessionId);
  const titleId = useId();
  if (found.data) return <QuizExclusions quiz={found.data} classSessionId={classSessionId} titleId={titleId} />;
  if (!found.isError) return null;
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") return null;
  return (
    <section aria-labelledby={titleId} className="mt-12 border-t border-hairline pt-8">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <div className="mt-3 flex flex-col items-start gap-2">
        <ActionError message={copy.loadFailed} />
        <Button onClick={() => void found.refetch()}>{nb.system.retry}</Button>
      </div>
    </section>
  );
}

function QuizExclusions({
  quiz,
  classSessionId,
  titleId,
}: {
  quiz: SessionQuiz;
  classSessionId: string;
  titleId: string;
}) {
  const queryClient = useQueryClient();
  const ids = useId();
  const helpId = `${ids}-help`;
  // The exclusions as switched, until «Lagre quizvalg»; null follows the api.
  const [draft, setDraft] = useState<readonly string[] | null>(null);
  const [saved, setSaved] = useState(false);
  const editable = quiz.can_exclude && quiz.open;
  const shown = new Set(draft ?? excludedIds(quiz));
  const save = useAction({
    mutationFn: async (excluded: readonly string[]) => {
      try {
        return await saveQuizExclusions(classSessionId, excluded);
      } catch (error) {
        // Closed meanwhile (the Test deadline passed, the Class archived): read the block again,
        // so it shows its read-only state instead of Bryters that can no longer save.
        if (error instanceof ApiRequestError && ["test_deadline_passed", "class_archived"].includes(error.code)) {
          void queryClient.invalidateQueries({ queryKey: sessionQuizKey(classSessionId) });
        }
        throw error;
      }
    },
    messages: {
      last_question: copy.lastQuestion,
      test_deadline_passed: copy.deadlinePassed,
      class_archived: copy.archived,
    },
    fallback: copy.failed,
    onSuccess: (result) => {
      queryClient.setQueryData(sessionQuizKey(classSessionId), result);
      setDraft(null);
      setSaved(true);
    },
  });
  const toggle = (id: string, included: boolean) => {
    const next = new Set(shown);
    if (included) next.delete(id);
    else next.add(id);
    setSaved(false);
    save.reset();
    setDraft(quiz.questions.filter((q) => next.has(q.id)).map((q) => q.id));
  };
  const readOnly = !quiz.can_exclude ? copy.assistant : !quiz.open ? copy.closed : null;
  const total = quiz.questions.length;
  return (
    <section aria-labelledby={titleId} className="mt-12 border-t border-hairline pt-8" data-quiz-exclusions="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <p id={helpId} className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>
        {copy.help}
      </p>
      {quiz.pinned ? null : <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.latest}</p>}
      {quiz.placeholder ? <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.placeholder}</p> : null}
      {readOnly ? <p className={`${LINE} mt-2 max-w-2xl text-ink`}>{readOnly}</p> : null}
      <ol className="mt-6 grid grid-cols-1 gap-x-16 gap-y-8 lg:grid-cols-3">
        {quiz.questions.map((question, i) => {
          const promptId = `${ids}-q${i}`;
          const included = !shown.has(question.id);
          return (
            <li key={question.id} data-quiz-question={question.id} className="min-w-0 border-t border-axis pt-3">
              <p className="text-caption text-ink-secondary">{copy.questionOf(i + 1, total)}</p>
              <p id={promptId} className={`${LINE} mt-1 font-semibold text-ink`}>
                {question.prompt}
              </p>
              <ul className="mt-2 flex flex-col gap-1">
                {question.choices.map((choice) => (
                  <li key={choice.id} className={`${LINE} text-ink-secondary`}>
                    {choice.text}
                  </li>
                ))}
              </ul>
              <p data-quiz-answer="" className={`${LINE} mt-2 text-ink`}>
                {copy.answer(answerText(question))}
              </p>
              {editable ? (
                <Switch
                  id={`${ids}-switch-${i}`}
                  className="mt-2"
                  checked={included}
                  onChange={(on) => toggle(question.id, on)}
                  labelledBy={promptId}
                  describedBy={helpId}
                >
                  {included ? copy.included : copy.excluded}
                </Switch>
              ) : (
                <p data-quiz-state="" className={`${LINE} mt-2 font-semibold text-ink`}>
                  {included ? copy.included : copy.excluded}
                </p>
              )}
            </li>
          );
        })}
      </ol>
      {editable ? (
        <div className="mt-8 flex flex-col items-start gap-3">
          <Button
            variant="secondary"
            unavailable={save.isPending}
            onClick={() => {
              if (save.isPending) return;
              setSaved(false);
              save.mutate(draft ?? excludedIds(quiz));
            }}
          >
            {save.isPending ? copy.saving : copy.save}
          </Button>
          <ActionError message={save.errorMessage} />
          <p role="status" className="text-body-phone text-ink">
            {saved && !save.isError ? copy.saved : ""}
          </p>
        </div>
      ) : null}
    </section>
  );
}
