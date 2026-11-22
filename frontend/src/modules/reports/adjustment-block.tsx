"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LINK_BUTTON } from "@/components/link";
import { SegmentedChoice } from "@/components/segmented-choice";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { errorCode, useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";

import { FACTOR_OPTIONS, type FactorChoice, checkShare, factorChoice, percentText, summaryText } from "./adjustment";
import { saveAdjustment, type StudentPage, studentPageKey } from "./api";

const copy = nb.reports.adjustment;

/**
 * The block «Tilrettelegging» on the Studentside (Story 8.9, FR-17, UX-DR53, EXPERIENCE.md →
 * Tilrettelegging), for the Lecturers of the Class: «Ingen tilrettelegging.» or the summary «Mer
 * tid: 2 ×. Andel uker: 60 %.», with the secondary «Endre tilrettelegging». The form opens in
 * place (one form at a time): «Mer tid før KI tar over» as Valgknapper, «Andel uker som kreves» from
 * 0 to the class share, the line on whom it concerns, the primary «Lagre tilrettelegging» and
 * «Avbryt». Focus moves to the chosen Valgknapp on open, back to the opener on «Avbryt», to the
 * share field when it is refused, and to «Lagret. Gjelder fra nå.» with the summary once saved.
 * There is no field for a reason.
 */
export function AdjustmentBlock({ data }: { data: StudentPage }) {
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState(0);
  const openerRef = useRef<HTMLButtonElement>(null);
  const savedRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (saved > 0) savedRef.current?.focus();
  }, [saved]);
  return (
    <section aria-labelledby={titleId} className="mt-8 max-w-xl border-t border-hairline pt-4" data-adjustment="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      {open ? (
        <AdjustmentForm
          data={data}
          onCancel={() => {
            setOpen(false);
            requestAnimationFrame(() => openerRef.current?.focus());
          }}
          onSaved={() => {
            setOpen(false);
            setSaved((n) => n + 1);
          }}
        />
      ) : (
        <div className="mt-3 flex flex-col items-start gap-3">
          <div
            ref={savedRef}
            tabIndex={-1}
            role={saved > 0 ? "status" : undefined}
            className="flex flex-col gap-1 text-body-phone text-ink focus:outline-none lg:text-body"
            data-adjustment-summary=""
          >
            {saved > 0 ? <p data-adjustment-saved="">{copy.saved}</p> : null}
            <p>{summaryText(data.adjustment)}</p>
          </div>
          <Button
            ref={openerRef}
            data-adjustment-open=""
            className="w-full lg:w-auto"
            onClick={() => {
              setSaved(0);
              setOpen(true);
            }}
          >
            {copy.change}
          </Button>
        </div>
      )}
    </section>
  );
}

function AdjustmentForm({ data, onCancel, onSaved }: { data: StudentPage; onCancel: () => void; onSaved: () => void }) {
  const ids = useId();
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLFormElement>(null);
  const shareRef = useRef<HTMLInputElement>(null);
  const [factor, setFactor] = useState<FactorChoice>(() => factorChoice(data.adjustment?.time_factor));
  const [share, setShare] = useState(() => String(data.adjustment?.share_percent ?? data.class_share));
  const [shareError, setShareError] = useState<string | undefined>(undefined);
  const [focusShare, setFocusShare] = useState(0);

  useEffect(() => {
    formRef.current?.querySelector<HTMLInputElement>('input[type="radio"]:checked')?.focus();
  }, []);
  useEffect(() => {
    if (focusShare > 0) shareRef.current?.focus();
  }, [focusShare]);

  const send = useAction({
    mutationFn: (body: { time_factor: number; share_percent: number }) =>
      saveAdjustment(data.class_session_id, data.user_id, body),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (page: StudentPage) => {
      queryClient.setQueryData(studentPageKey(data.class_session_id, data.user_id), page);
      onSaved();
    },
  });

  const refuseShare = (message: string) => {
    setShareError(message);
    setFocusShare((n) => n + 1);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (send.isPending) return;
    send.reset();
    const checked = checkShare(share, data.class_share);
    if ("error" in checked) {
      refuseShare(checked.error);
      return;
    }
    send.mutate(
      { time_factor: Number(factor), share_percent: checked.share },
      {
        onError: (failure) => {
          const fields = failure instanceof ApiRequestError ? failure.fields : {};
          if (errorCode(failure) === "invalid_adjustment" && fields.share_percent) {
            send.reset();
            refuseShare(nb.reports.adjustment.shareError(data.class_share));
          }
        },
      },
    );
  };

  const scopeId = `${ids}-scope`;
  return (
    <form
      ref={formRef}
      noValidate
      aria-labelledby={`${ids}-title`}
      data-adjustment-form=""
      className="mt-3 flex w-full flex-col items-start gap-4 rounded-sm border border-axis bg-paper px-4 py-4"
      onSubmit={submit}
    >
      <p id={`${ids}-title`} className="sr-only">
        {copy.change}
      </p>
      <SegmentedChoice
        name={`${ids}-factor`}
        legend={copy.factorLegend}
        options={FACTOR_OPTIONS}
        value={factor}
        onChange={(value) => {
          setFactor(value);
          if (send.isError) send.reset();
        }}
        className="w-full"
      />
      <TextField
        id={`${ids}-share`}
        ref={shareRef}
        label={copy.shareLabel}
        inputMode="numeric"
        autoComplete="off"
        value={share}
        hint={copy.classShare(percentText(data.class_share))}
        error={shareError}
        className="w-full"
        inputClassName="max-w-[8rem]"
        onChange={(event) => {
          setShare(event.target.value);
          setShareError(undefined);
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
          data-adjustment-save=""
          className="w-full lg:w-auto"
          aria-describedby={scopeId}
          unavailable={send.isPending}
        >
          {copy.save}
        </Button>
        <button
          type="button"
          data-adjustment-cancel=""
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
