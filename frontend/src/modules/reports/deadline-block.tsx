"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LINK_BUTTON } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { errorCode, useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";
import { osloDateText, toOsloInput } from "@/modules/sessions/dates";

import { extendTestDeadline, type ManagedStudentPage, studentPageKey } from "./api";
import { canExtend, checkDeadline, deadlineLines, refusalOnField, type StudentDeadlines } from "./deadline";

const copy = nb.reports.deadline;

/**
 * The block «Frister» on the Studentside (Story 11.13, FR-18), for the Lecturers of the Class: the
 * Student's Testfrist and Debrieffrist, whether they are the Class session's or extended, and the
 * secondary «Forleng testfrist». The form opens in place, one form at a time on the page (`open`
 * and `onOpenChange` are the page's): «Ny testfrist» as a date and time in Europe/Oslo, prefilled
 * with the Student's date, the Class's date in the help line, the line on what moves and whom it
 * concerns, the primary «Lagre frist» and «Avbryt». A refused date is said on the field, which takes
 * focus; once saved, «Lagret. Ny testfrist for …» replaces the form and takes focus. A Student who
 * has handed the test in has no button, only the line saying so. There is no field for a reason.
 */
export function DeadlineBlock({
  data,
  open,
  onOpenChange,
}: {
  data: ManagedStudentPage;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const titleId = useId();
  const [saved, setSaved] = useState<string | null>(null);
  const [focusSaved, setFocusSaved] = useState(0);
  const openerRef = useRef<HTMLButtonElement>(null);
  const savedRef = useRef<HTMLDivElement>(null);
  const deadlines = data.deadlines;
  useEffect(() => {
    if (focusSaved > 0) savedRef.current?.focus();
  }, [focusSaved]);
  const classTest = deadlines.class_test_deadline;
  return (
    <section aria-labelledby={titleId} className="mt-8 max-w-2xl border-t border-hairline pt-4" data-deadline="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      {open && canExtend(deadlines) && classTest ? (
        <DeadlineForm
          data={data}
          classTestDeadline={classTest}
          onCancel={() => {
            onOpenChange(false);
            requestAnimationFrame(() => openerRef.current?.focus());
          }}
          onSaved={(block) => {
            onOpenChange(false);
            setSaved(block.test_deadline ? copy.saved(data.name, osloDateText(block.test_deadline)) : null);
            setFocusSaved((n) => n + 1);
          }}
        />
      ) : (
        <div className="mt-3 flex flex-col items-start gap-3">
          <div
            ref={savedRef}
            tabIndex={-1}
            role={saved ? "status" : undefined}
            className="flex flex-col gap-1 text-body-phone text-ink focus:outline-none lg:text-body"
            data-deadline-summary=""
          >
            {saved ? <p data-deadline-saved="">{saved}</p> : null}
            {deadlineLines(deadlines).map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
          {deadlines.submitted ? (
            <p className="text-body-phone text-ink-secondary lg:text-body" data-deadline-submitted="">
              {copy.submitted(data.name)}
            </p>
          ) : canExtend(deadlines) ? (
            <Button
              ref={openerRef}
              data-deadline-open=""
              className="w-full lg:w-auto"
              onClick={() => {
                setSaved(null);
                onOpenChange(true);
              }}
            >
              {copy.change}
            </Button>
          ) : null}
        </div>
      )}
    </section>
  );
}

function DeadlineForm({
  data,
  classTestDeadline,
  onCancel,
  onSaved,
}: {
  data: ManagedStudentPage;
  classTestDeadline: string;
  onCancel: () => void;
  onSaved: (block: StudentDeadlines) => void;
}) {
  const ids = useId();
  const queryClient = useQueryClient();
  const fieldRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState(() => toOsloInput(data.deadlines.test_deadline));
  const [error, setError] = useState<string | undefined>(undefined);
  const [focusField, setFocusField] = useState(1);

  useEffect(() => {
    if (focusField > 0) fieldRef.current?.focus();
  }, [focusField]);

  const pageKey = studentPageKey(data.class_session_id, data.user_id);
  const send = useAction({
    mutationFn: (at: string) => extendTestDeadline(data.class_session_id, data.user_id, at),
    messages: { ...copy.refusals, invalid_extension: copy.refusals.no_test_deadline },
    fallback: copy.failed,
    onSuccess: (block: StudentDeadlines) => {
      queryClient.setQueryData<ManagedStudentPage>(pageKey, (page) => (page ? { ...page, deadlines: block } : page));
      onSaved(block);
    },
  });

  const refuse = (message: string) => {
    setError(message);
    setFocusField((n) => n + 1);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (send.isPending) return;
    send.reset();
    const checked = checkDeadline(value, classTestDeadline, Date.now());
    if ("error" in checked) {
      refuse(checked.error);
      return;
    }
    send.mutate(checked.at, {
      onError: (failure) => {
        if (errorCode(failure) === "attempt_submitted") void queryClient.invalidateQueries({ queryKey: pageKey });
        const reason = failure instanceof ApiRequestError ? failure.fields.test_deadline : undefined;
        const onField = errorCode(failure) === "invalid_extension" ? refusalOnField(reason, classTestDeadline) : undefined;
        if (onField) {
          send.reset();
          refuse(onField);
        }
      },
    });
  };

  const scopeId = `${ids}-scope`;
  return (
    <form
      noValidate
      aria-labelledby={`${ids}-title`}
      data-deadline-form=""
      className="mt-3 flex w-full flex-col items-start gap-4 rounded-sm border border-axis bg-paper px-4 py-4"
      onSubmit={submit}
    >
      <p id={`${ids}-title`} className="sr-only">
        {copy.change}
      </p>
      <TextField
        id={`${ids}-at`}
        ref={fieldRef}
        type="datetime-local"
        label={copy.fieldLabel}
        value={value}
        hint={copy.hint(osloDateText(classTestDeadline))}
        error={error}
        className="w-full"
        inputClassName="max-w-[16rem]"
        onChange={(event) => {
          setValue(event.target.value);
          setError(undefined);
          if (send.isError) send.reset();
        }}
      />
      <p id={scopeId} className="text-body-phone text-ink lg:text-body">
        {copy.scope(data.name)}
      </p>
      <div className="flex w-full flex-col items-stretch gap-x-6 gap-y-2 lg:flex-row lg:items-center">
        <Button
          type="submit"
          variant="primary"
          data-deadline-save=""
          className="w-full lg:w-auto"
          aria-describedby={scopeId}
          unavailable={send.isPending}
        >
          {copy.save}
        </Button>
        <button
          type="button"
          data-deadline-cancel=""
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
