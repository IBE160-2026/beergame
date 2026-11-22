"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LINK_BUTTON } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";
import { fromOsloInput, osloWeekdayTime, toOsloInput } from "@/modules/sessions/dates";

import {
  classOverviewKey,
  endPause,
  type GameInsight,
  gameInsightKey,
  type InsightPause,
  pauseGameAsLecturer,
  setPauseAgreedTime,
} from "./api";
import { checkProposal, type ProposalErrors, type ProposalField, refusedRange } from "./time-proposal";

const copy = nb.spillstyring.pause;
const errors = nb.games.timeProposal.errors;

/** The form as typed: a date «2026-11-26» and a time «19:00» in Europe/Oslo, or «Uten avtalt tid». */
export type AgreedInputs = { date: string; time: string; noTime: boolean };
export const EMPTY_AGREED: AgreedInputs = { date: "", time: "", noTime: false };

/** «Endre avtalt tid» opens the form with the agreed time in force, or empty without one. */
export function agreedInputs(resumeAt: string | null | undefined): AgreedInputs {
  const local = toOsloInput(resumeAt);
  if (!local) return EMPTY_AGREED;
  const [date = "", time = ""] = local.split("T");
  return { date, time: time.slice(0, 5), noTime: false };
}

/** The agreed time the form holds (ISO), or null with «Uten avtalt tid» or a half-typed time. */
export function agreedAt(inputs: AgreedInputs): string | null {
  if (inputs.noTime || !inputs.date || !inputs.time) return null;
  return fromOsloInput(`${inputs.date}T${inputs.time}`);
}

/**
 * What the form says before anything is sent (Story 8.7, AD-10): nothing with «Uten avtalt tid»;
 * else a missing field its reason, and a time not after `now` (ms) or after the Spillfrist
 * «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» under the time field. The api judges the
 * same rule again (`time_out_of_range`). Without a Spillfrist only «after now» is checked here.
 */
export function checkAgreed(
  inputs: AgreedInputs,
  now: number,
  playDeadline: string | null | undefined,
  halfTyped: Partial<Record<ProposalField, boolean>> = {},
): ProposalErrors {
  if (inputs.noTime) return {};
  if (playDeadline) return checkProposal(inputs, now, playDeadline, halfTyped);
  const found: ProposalErrors = {};
  if (halfTyped.date || !inputs.date) found.date = errors.dateMissing;
  if (halfTyped.time || !inputs.time) found.time = errors.timeMissing;
  if (found.date || found.time) return found;
  const at = agreedAt(inputs);
  if (at === null) return { date: errors.dateMissing };
  if (!(Date.parse(at) > now)) found.time = copy.afterNow;
  return found;
}

export type PauseMode = "pause" | "change";

/** The primary: «Ta pause til to. 19:00», «Ta pause uten avtalt tid», or «Ta pause til …» while no
 * time is chosen; in «Endre avtalt tid» «Lagre avtalt tid to. 19:00» and «Lagre uten avtalt tid». */
export function confirmLabel(mode: PauseMode, inputs: AgreedInputs): string {
  const at = agreedAt(inputs);
  if (mode === "pause") {
    if (inputs.noTime) return copy.confirmNoTime;
    return at ? copy.confirmAt(osloWeekdayTime(at)) : copy.confirm;
  }
  if (inputs.noTime) return copy.saveNoTime;
  return at ? copy.saveAt(osloWeekdayTime(at)) : copy.save;
}

/** The result line that replaces the form: «Pause til to. 19:00 er satt.» or without a time. */
export function doneText(resumeAt: string | null): string {
  return resumeAt ? copy.doneAt(osloWeekdayTime(resumeAt)) : copy.doneNoTime;
}

/** Spillinnsikt → Paused: «Pause siden ma. 14:10, satt av Sara.» or «… satt av deg.», then
 * «Avtalt tid to. 19:00.» when there is one. */
export function insightPauseText(pause: InsightPause): string {
  const since = osloWeekdayTime(pause.paused_at);
  const line = pause.mine ? copy.sinceMine(since) : copy.since(since, pause.by ?? null);
  return pause.resume_at ? `${line} ${copy.agreed(osloWeekdayTime(pause.resume_at))}` : line;
}

/** After a Pause command: Spillinnsikt is the answer; it and the Oversikt read again. */
function useReread(gameId: string, sessionId: string) {
  const queryClient = useQueryClient();
  return {
    set: (insight: GameInsight) => queryClient.setQueryData(gameInsightKey(gameId), insight),
    reread: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: gameInsightKey(gameId) }),
        queryClient.invalidateQueries({ queryKey: classOverviewKey(sessionId) }),
      ]),
  };
}

/**
 * The Lecturer's pause form (Story 8.7, FR-89, UX-DR52, EXPERIENCE.md → Spillstyring → Pause), in
 * place in Spillstyring or under the Varselbånd: «Når fortsetter spillet?» with «Dato» and
 * «Klokkeslett» from now to the Spillfrist, or «Uten avtalt tid»; the two consequence lines; the
 * primary «Ta pause til to. 19:00» (or «Ta pause uten avtalt tid») and «Avbryt». In `change` mode
 * («Endre avtalt tid») it is prefilled and saves the agreed time. Focus moves to «Dato» on open and
 * to the first refused field; a time out of range is said on leaving the field and on the press,
 * in the Ordrefelt error pattern. `now` is the clock the hint uses (ms); the api judges again.
 */
export function StaffPauseForm({
  gameId,
  sessionId,
  mode,
  resumeAt = null,
  playDeadline,
  now,
  onCancel,
  onDone,
  className,
}: {
  gameId: string;
  sessionId: string;
  mode: PauseMode;
  resumeAt?: string | null;
  playDeadline: string | null | undefined;
  now: () => number;
  onCancel: () => void;
  /** The result line's text, once the api has answered (or someone paused first). */
  onDone: (text: string) => void;
  className?: string;
}) {
  const ids = useId();
  const store = useReread(gameId, sessionId);
  const [inputs, setInputs] = useState<AgreedInputs>(() => (mode === "change" ? agreedInputs(resumeAt) : EMPTY_AGREED));
  const [found, setFound] = useState<ProposalErrors>({});
  const fields = { date: useRef<HTMLInputElement>(null), time: useRef<HTMLInputElement>(null) };
  const [focus, setFocus] = useState<{ field: ProposalField; n: number }>({ field: "date", n: 0 });
  useEffect(() => fields[focus.field].current?.focus(), [focus]);

  const send = useAction({
    mutationFn: (at: string | null) => (mode === "pause" ? pauseGameAsLecturer(gameId, at) : setPauseAgreedTime(gameId, at)),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (insight: GameInsight, at: string | null) => {
      store.set(insight);
      void store.reread();
      onDone(doneText(at));
    },
  });

  const halfTyped = () => ({
    date: fields.date.current?.validity.badInput,
    time: fields.time.current?.validity.badInput,
  });
  const refuse = (next: ProposalErrors) => {
    setFound(next);
    const first = (["date", "time"] as const).find((field) => next[field]);
    if (first) setFocus((prev) => ({ field: first, n: prev.n + 1 }));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (send.isPending) return;
    send.reset();
    const checked = checkAgreed(inputs, now(), playDeadline, halfTyped());
    if (checked.date || checked.time) {
      refuse(checked);
      return;
    }
    send.mutate(agreedAt(inputs), {
      onError: (failure) => {
        const range = playDeadline
          ? refusedRange(failure, playDeadline)
          : errorCode(failure) === "time_out_of_range"
            ? { time: copy.afterNow }
            : null;
        if (range) {
          send.reset();
          refuse(range);
          return;
        }
        // Someone paused first: once read again, the line in Spillstyring says who.
        if (errorCode(failure) === "already_paused") {
          void store.reread().then(() => onDone(copy.already));
          return;
        }
        void store.reread();
      },
    });
  };

  // On leaving a field: the range rule once both are typed (EXPERIENCE.md → Ordrefelt errors).
  const leave = () => {
    if (!inputs.date || !inputs.time || inputs.noTime) return;
    const checked = checkAgreed(inputs, now(), playDeadline, halfTyped());
    setFound((prev) => ({ ...prev, time: checked.time }));
  };

  const change = (next: Partial<AgreedInputs>) => {
    setInputs((prev) => ({ ...prev, ...next }));
    setFound({});
    if (send.isError) send.reset();
  };

  const linesId = `${ids}-lines`;
  return (
    <form
      noValidate
      aria-labelledby={`${ids}-title`}
      data-staff-pause={mode}
      className={cn("flex w-full max-w-xl flex-col items-start gap-4 rounded-sm border border-axis bg-paper px-4 py-4", className)}
      onSubmit={submit}
    >
      <fieldset className="m-0 flex w-full min-w-0 flex-col gap-4 border-0 p-0">
        <legend id={`${ids}-title`} className="mb-field-gap text-label text-ink">
          {copy.title}
        </legend>
        <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
          <TextField
            id={`${ids}-date`}
            ref={fields.date}
            type="date"
            label={copy.date}
            value={inputs.date}
            readOnly={inputs.noTime}
            error={inputs.noTime ? undefined : found.date}
            onChange={(event) => change({ date: event.target.value })}
            onBlur={leave}
          />
          <TextField
            id={`${ids}-time`}
            ref={fields.time}
            type="time"
            label={copy.time}
            value={inputs.time}
            readOnly={inputs.noTime}
            errorAlert
            error={inputs.noTime ? undefined : found.time}
            onChange={(event) => change({ time: event.target.value })}
            onBlur={leave}
          />
        </div>
        {/* «Uten avtalt tid»: a native checkbox over the whole 44 px row (transparent), so the tap
            target is the row; the box beside the text is drawn from its state. */}
        <label className="group relative inline-flex min-h-tap-target-min cursor-pointer items-center gap-3 self-start rounded-sm pr-2 text-body-phone text-ink has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink lg:text-body">
          <input
            type="checkbox"
            data-pause-no-time=""
            className="absolute inset-0 m-0 size-full cursor-pointer opacity-0"
            checked={inputs.noTime}
            onChange={(event) => change({ noTime: event.target.checked })}
          />
          <span
            aria-hidden="true"
            className="flex size-5 shrink-0 items-center justify-center rounded-sm border border-ink-muted bg-paper group-hover:border-ink group-has-checked:border-ink group-has-checked:bg-ink group-has-checked:text-paper"
          >
            <svg viewBox="0 0 16 16" className="hidden size-3.5 group-has-checked:block" fill="none">
              <path d="M3 8.5l3 3 7-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          {copy.noTime}
        </label>
      </fieldset>
      <div id={linesId} className="flex flex-col gap-2">
        <p className="text-body-phone text-ink lg:text-body">{copy.noTakeover}</p>
        <p className="text-body-phone text-ink-secondary lg:text-body">{copy.afterTime}</p>
      </div>
      <div className="flex w-full flex-col items-stretch gap-x-6 gap-y-2 lg:flex-row lg:items-center">
        <Button
          type="submit"
          variant="primary"
          data-staff-pause-confirm=""
          className="w-full lg:w-auto"
          aria-describedby={linesId}
          unavailable={send.isPending}
        >
          {confirmLabel(mode, inputs)}
        </Button>
        <button
          type="button"
          data-staff-pause-cancel=""
          className={cn(LINK_BUTTON, "self-start")}
          onClick={() => {
            if (!send.isPending) onCancel();
          }}
        >
          {copy.cancel}
        </button>
      </div>
      {errorCode(send.error) === "already_paused" || errorCode(send.error) === "time_out_of_range" ? null : (
        <ActionError message={send.errorMessage} />
      )}
    </form>
  );
}

/** One press, no dialog: «Avslutt pausen» (Story 8.7). The result line replaces the paused state. */
export function useEndPause(gameId: string, sessionId: string, onDone: (text: string) => void) {
  const store = useReread(gameId, sessionId);
  return useAction({
    mutationFn: () => endPause(gameId),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (insight: GameInsight) => {
      store.set(insight);
      void store.reread();
      onDone(copy.ended);
    },
  });
}

/** The result line that replaces a closed form and takes focus (`tabindex="-1"`, `role="status"`). */
export function PauseResult({ text, n, className }: { text: string; n: number; className?: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (n > 0) ref.current?.focus();
  }, [n]);
  return (
    <p
      ref={ref}
      tabIndex={-1}
      role="status"
      data-pause-result=""
      className={cn("text-body-phone text-ink focus:outline-none lg:text-body", !text && "sr-only", className)}
    >
      {text}
    </p>
  );
}
