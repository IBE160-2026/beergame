"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LINK_BUTTON } from "@/components/link";
import { SegmentedChoice } from "@/components/segmented-choice";
import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { errorCode, useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";

import { correctCompletion, studentRecordKey } from "./api";
import {
  type CompletionRow,
  type CompletionStep,
  completionRows,
  participationLines,
  requirementLine,
  type StudentRecord,
} from "./record";

const copy = nb.reports.completion;

/** The longest «Begrunnelse», as the api counts it (trimmed) [ASSUMPTION]. */
const REASON_MAX = 1000;

type Choice = "done" | "not_done";

/**
 * The block «Fullføring» on the Studentside (Story 13.2, FR-17, UX-DR54, DESIGN.md →
 * Fullføringsretting): one row per step (Klassespill, Debrief, Debrief-quiz, Replay, Individuell
 * test) with its status in text, «gjort» or «ikke gjort», never by a mark alone; the Klassespill
 * row carries the share lines, and the requirement line shows only for an obligatory Class session.
 * Every value is the api's, from `reports.service.completion_status`. Under it, «Til informasjon»:
 * the time on the Student's own Orders and whether they were constant, which never change the
 * status.
 *
 * Story 13.3: for a Lecturer of an obligatory Class session (`can_correct`), each row ends in the
 * secondary «Rett Klassespill» (and so on), which opens the correction form in place. `editing`
 * and `onEditingChange` are the page's, so one in-place form is open on the Studentside at a time.
 * Focus moves to the chosen Valgknapp on open and back to the opener on «Avbryt»; once saved, the
 * row's status line «Gjort, rettet av Bård 12. des.» replaces the form and takes focus, with the
 * reason under it.
 */
export function CompletionBlock({
  record,
  editing = null,
  onEditingChange = () => {},
}: {
  record: StudentRecord;
  editing?: string | null;
  onEditingChange?: (step: string | null) => void;
}) {
  const titleId = useId();
  const infoId = useId();
  const completion = record.completion;
  const requirement = completion ? requirementLine(completion) : null;
  const openers = useRef(new Map<string, HTMLButtonElement>());
  const statuses = useRef(new Map<string, HTMLParagraphElement>());
  const [saved, setSaved] = useState<{ step: string; n: number } | null>(null);
  useEffect(() => {
    if (saved) statuses.current.get(saved.step)?.focus();
  }, [saved]);
  const steps = new Map<string, CompletionStep>((completion?.steps ?? []).map((step) => [step.step, step]));
  return (
    <section aria-labelledby={titleId} className="mt-8 max-w-2xl border-t border-hairline pt-4" data-completion="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      {completion ? (
        <>
          {requirement ? (
            <p className="mt-2 text-body-phone text-ink lg:text-body" data-requirement="">
              {requirement}
            </p>
          ) : null}
          <ul className="mt-3 border-t border-hairline">
            {completionRows(completion).map((row) => (
              <li
                key={row.step}
                className="border-b border-hairline py-2 sm:grid sm:grid-cols-[minmax(0,10rem)_minmax(0,1fr)] sm:gap-x-4"
                data-step={row.step}
                data-done={row.done ? "true" : "false"}
                data-corrected={row.corrected ? "true" : undefined}
              >
                <p className="text-label text-ink">{row.name}</p>
                <div className="flex min-w-0 flex-col gap-1">
                  <p
                    ref={(node) => {
                      if (node) statuses.current.set(row.step, node);
                      else statuses.current.delete(row.step);
                    }}
                    tabIndex={saved?.step === row.step ? -1 : undefined}
                    role={saved?.step === row.step ? "status" : undefined}
                    className="text-body-phone text-ink focus:outline-none lg:text-body"
                    data-step-status=""
                  >
                    {row.status}
                  </p>
                  {row.reason ? (
                    <p
                      className="text-body-phone text-ink-secondary [overflow-wrap:anywhere] whitespace-pre-line lg:text-body"
                      data-step-reason=""
                    >
                      {row.reason}
                    </p>
                  ) : null}
                  {row.lines.map((line) => (
                    <p
                      key={line}
                      className="text-body-phone text-ink-secondary tabular-nums lining-nums [overflow-wrap:anywhere] lg:text-body"
                    >
                      {line}
                    </p>
                  ))}
                  {record.can_correct ? (
                    editing === row.step ? (
                      <CorrectionForm
                        record={record}
                        row={row}
                        step={steps.get(row.step)!}
                        onCancel={() => {
                          onEditingChange(null);
                          requestAnimationFrame(() => openers.current.get(row.step)?.focus());
                        }}
                        onSaved={() => {
                          onEditingChange(null);
                          setSaved((now) => ({
                            step: row.step,
                            n: (now?.n ?? 0) + 1,
                          }));
                        }}
                      />
                    ) : (
                      <Button
                        ref={(node: HTMLButtonElement | null) => {
                          if (node) openers.current.set(row.step, node);
                          else openers.current.delete(row.step);
                        }}
                        data-correct-open={row.step}
                        className="mt-1 w-full lg:w-auto lg:self-start"
                        onClick={() => {
                          setSaved(null);
                          onEditingChange(row.step);
                        }}
                      >
                        {copy.correct(row.name)}
                      </Button>
                    )
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.unavailable}</p>
      )}
      <div className="mt-4" role="group" aria-labelledby={infoId} data-participation="">
        <h3 id={infoId} className="text-label text-ink">
          {copy.infoTitle}
        </h3>
        <p className="text-caption text-ink-secondary">{copy.infoNote}</p>
        {participationLines(record.participation).map((line) => (
          <p key={line} className="mt-1 text-body-phone text-ink tabular-nums lining-nums lg:text-body">
            {line}
          </p>
        ))}
      </div>
    </section>
  );
}

/** The correction form of one step (Story 13.3, UX-DR54): Valgknapper «Gjort» / «Ikke gjort»
 * (the opposite of the step's status chosen first: what a correction usually sets), the required
 * «Begrunnelse», the line on what is logged, «Lagre retting» and «Avbryt». An empty reason is
 * refused here, before any request, and by the api alike. */
function CorrectionForm({
  record,
  row,
  step,
  onCancel,
  onSaved,
}: {
  record: StudentRecord;
  row: CompletionRow;
  step: CompletionStep;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const ids = useId();
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLFormElement>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const [choice, setChoice] = useState<Choice>(step.done ? "not_done" : "done");
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | undefined>(undefined);
  const [focusReason, setFocusReason] = useState(0);

  useEffect(() => {
    formRef.current?.querySelector<HTMLInputElement>('input[type="radio"]:checked')?.focus();
  }, []);
  useEffect(() => {
    if (focusReason > 0) reasonRef.current?.focus();
  }, [focusReason]);

  const send = useAction({
    mutationFn: (body: { step: CompletionStep["step"]; done: boolean; reason: string }) =>
      correctCompletion(record.class_session_id, record.user_id, body),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (next: StudentRecord) => {
      queryClient.setQueryData(studentRecordKey(record.class_session_id, record.user_id), next);
      onSaved();
    },
  });

  const refuseReason = (message: string) => {
    setReasonError(message);
    setFocusReason((n) => n + 1);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (send.isPending) return;
    send.reset();
    const trimmed = reason.trim();
    if (!trimmed) {
      refuseReason(copy.reasonError);
      return;
    }
    // In characters, as the api counts them, not UTF-16 units.
    if ([...trimmed].length > REASON_MAX) {
      refuseReason(copy.reasonTooLong);
      return;
    }
    send.mutate(
      { step: step.step, done: choice === "done", reason: trimmed },
      {
        onError: (failure) => {
          const fields = failure instanceof ApiRequestError ? failure.fields : {};
          if (errorCode(failure) === "invalid_correction" && fields.reason) {
            send.reset();
            refuseReason(fields.reason === "too_long" ? copy.reasonTooLong : copy.reasonError);
          }
        },
      },
    );
  };

  const loggedId = `${ids}-logged`;
  return (
    <form
      ref={formRef}
      noValidate
      aria-labelledby={`${ids}-title`}
      data-correct-form={row.step}
      className="mt-2 flex w-full flex-col items-start gap-4 rounded-sm border border-axis bg-paper px-4 py-4"
      onSubmit={submit}
    >
      <p id={`${ids}-title`} className="sr-only">
        {copy.correct(row.name)}
      </p>
      <SegmentedChoice
        name={`${ids}-status`}
        legend={copy.statusLegend}
        options={[
          { value: "done", label: copy.doneChoice },
          { value: "not_done", label: copy.notDoneChoice },
        ]}
        value={choice}
        onChange={(value) => {
          setChoice(value);
          if (send.isError) send.reset();
        }}
        className="w-full"
      />
      <TextAreaField
        id={`${ids}-reason`}
        ref={reasonRef}
        label={copy.reasonLabel}
        value={reason}
        error={reasonError}
        rows={3}
        className="w-full"
        data-correct-reason=""
        onChange={(event) => {
          setReason(event.target.value);
          setReasonError(undefined);
          if (send.isError) send.reset();
        }}
      />
      <p id={loggedId} className="text-body-phone text-ink lg:text-body">
        {copy.logged}
      </p>
      <div className="flex w-full flex-col items-stretch gap-x-6 gap-y-2 lg:flex-row lg:items-center">
        <Button
          type="submit"
          variant="primary"
          data-correct-save=""
          className="w-full lg:w-auto"
          aria-describedby={loggedId}
          unavailable={send.isPending}
        >
          {copy.save}
        </Button>
        <button
          type="button"
          data-correct-cancel=""
          className={cn(LINK_BUTTON, "self-start")}
          onClick={() => {
            if (!send.isPending) onCancel();
          }}
        >
          {copy.cancel}
        </button>
      </div>
      <ActionError message={send.errorMessage} />
    </form>
  );
}
