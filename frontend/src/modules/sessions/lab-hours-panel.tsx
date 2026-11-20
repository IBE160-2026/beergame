"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import { addLabHour, changeLabHour, type ClassSession, classSessionKey, type LabHour, removeLabHour } from "./api";
import {
  checkLabHour,
  EMPTY_LAB_HOUR,
  firstRefusedField,
  type HalfTyped,
  inputsOfLabHour,
  type LabHourErrors,
  type LabHourField,
  labHourBody,
  labHourLine,
  labHourRefusal,
  PLACE_MAX,
  placesOf,
  withLabHour,
} from "./lab-hours";

const copy = nb.sessions.labHours;

const PANEL = "flex w-full flex-col items-start gap-4 rounded-sm border border-axis px-4 py-4";

type Open = { mode: "add" } | { mode: "edit"; lab: LabHour } | null;

/** The Lab hour ended, or was removed elsewhere, while its form was open. */
function stale(failure: unknown): boolean {
  const code = errorCode(failure);
  return code === "lab_hour_ended" || code === "forbidden";
}

/**
 * The Lab hours under the Datolinje (Story 5.6, FR-19, UX-DR51): the legend «Blå firkant: Labtime,
 * {sted}.», the Lenke «Legg til Labtime» and the list «Labtimer», which is the squares' text
 * alternative. Each Lab hour that has not ended has a Lenke «Endre». Both open one in-place form;
 * a save or removal takes effect at once, not with «Lagre Klasseøkt», and focus moves to the
 * result line. `onOpenChange` tells the page a form is open, so «Lagre Klasseøkt» steps back.
 */
export function LabHours({ item, onOpenChange }: { item: ClassSession; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient();
  const ids = useId();
  const [open, setOpenState] = useState<Open>(null);
  const [result, setResult] = useState<{ text: string; n: number }>({ text: "", n: 0 });
  const resultRef = useRef<HTMLParagraphElement>(null);
  const addRef = useRef<HTMLButtonElement>(null);
  const editRefs = useRef(new Map<string, HTMLButtonElement>());
  const labs = item.lab_hours;
  const manage = item.can_manage;

  useEffect(() => {
    if (result.n > 0) resultRef.current?.focus();
  }, [result]);

  const setOpen = (next: Open) => {
    setOpenState(next);
    onOpenChange(next !== null);
  };
  const close = (opener: () => HTMLButtonElement | null | undefined) => {
    setOpen(null);
    // After the form unmounts and its Lenke is back, focus that Lenke.
    requestAnimationFrame(() => opener()?.focus());
  };
  // The Lab hour being changed was removed or has ended (read again after a refusal): close.
  const editedId = open?.mode === "edit" ? open.lab.id : null;
  const editedGone = editedId !== null && !labs.some((lab) => lab.id === editedId && !lab.ended);
  useEffect(() => {
    if (editedGone) {
      setOpenState(null);
      onOpenChange(false);
    }
  }, [editedGone, onOpenChange]);
  const reread = () => void queryClient.invalidateQueries({ queryKey: classSessionKey(item.id), exact: true });
  const done = (text: string, next: LabHour[]) => {
    queryClient.setQueryData<ClassSession>(classSessionKey(item.id), (old) => (old ? { ...old, lab_hours: next } : old));
    setOpen(null);
    setResult((prev) => ({ text, n: prev.n + 1 }));
  };

  return (
    <div className="mt-4">
      {labs.length > 0 || manage ? (
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
          {labs.length > 0 ? (
            <p className="flex items-center gap-2 text-body-phone text-ink-secondary">
              <svg aria-hidden="true" focusable="false" width="8" height="8" className="shrink-0">
                <rect width="8" height="8" fill="var(--color-lager)" />
              </svg>
              {copy.legend(placesOf(labs))}
            </p>
          ) : (
            <span />
          )}
          {manage && open?.mode !== "add" ? (
            <button
              ref={addRef}
              type="button"
              className={LINK_BUTTON}
              onClick={() => {
                setResult((prev) => ({ text: "", n: prev.n }));
                setOpen({ mode: "add" });
              }}
            >
              {copy.add}
            </button>
          ) : null}
        </div>
      ) : null}
      {open?.mode === "add" ? (
        <LabHourForm
          idPrefix={`${ids}-add`}
          sessionId={item.id}
          onCancel={() => close(() => addRef.current)}
          onSaved={(lab) => done(copy.added, withLabHour(labs, lab))}
          onStale={reread}
        />
      ) : null}
      <h3 id={`${ids}-title`} className="mt-4 text-label text-ink">
        {copy.title}
      </h3>
      {labs.length === 0 ? (
        <p className="mt-1 text-body-phone text-ink-secondary">{copy.none}</p>
      ) : (
        <ul aria-labelledby={`${ids}-title`} className="mt-1 flex flex-col">
          {labs.map((lab) => {
            const line = labHourLine(lab);
            const editing = open?.mode === "edit" && open.lab.id === lab.id;
            return (
              <li key={lab.id} className="flex flex-col">
                <div className="flex min-h-tap-target-min flex-wrap items-center justify-between gap-x-6">
                  <span className={lab.ended ? "text-body-phone text-ink-secondary" : "text-body-phone text-ink"}>
                    {line}
                    {lab.ended ? ` (${copy.ended})` : null}
                  </span>
                  {manage && !lab.ended && !editing ? (
                    <button
                      ref={(node) => {
                        if (node) editRefs.current.set(lab.id, node);
                        else editRefs.current.delete(lab.id);
                      }}
                      type="button"
                      className={LINK_BUTTON}
                      aria-label={copy.editLabel(line)}
                      onClick={() => {
                        setResult((prev) => ({ text: "", n: prev.n }));
                        setOpen({ mode: "edit", lab });
                      }}
                    >
                      {copy.edit}
                    </button>
                  ) : null}
                </div>
                {editing ? (
                  <LabHourForm
                    idPrefix={`${ids}-edit`}
                    sessionId={item.id}
                    lab={lab}
                    onCancel={() => close(() => editRefs.current.get(lab.id) ?? addRef.current)}
                    onSaved={(saved) => done(copy.changed, withLabHour(labs, saved))}
                    onRemoved={() => done(copy.removed, withLabHour(labs, null, lab.id))}
                    onStale={reread}
                  />
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
      <p ref={resultRef} tabIndex={-1} role="status" className="mt-2 text-body-phone text-ink focus:outline-none">
        {result.text}
      </p>
    </div>
  );
}

/**
 * The in-place form of one Lab hour (Story 5.6): «Dato», «Start», «Slutt» and «Sted», the
 * consequence, the primary save, «Fjern Labtimen» when it changes a saved one, and «Avbryt».
 * Focus moves to «Dato» on open and to the first refused field on a refusal.
 */
function LabHourForm({
  idPrefix,
  sessionId,
  lab,
  onCancel,
  onSaved,
  onRemoved,
  onStale,
}: {
  idPrefix: string;
  sessionId: string;
  lab?: LabHour;
  onCancel: () => void;
  onSaved: (lab: LabHour) => void;
  onRemoved?: () => void;
  /** The api said the Lab hour has ended or is gone: the page reads the session again. */
  onStale: () => void;
}) {
  const [inputs, setInputs] = useState(() => (lab ? inputsOfLabHour(lab) : EMPTY_LAB_HOUR));
  const [errors, setErrors] = useState<LabHourErrors>({});
  const fields = {
    date: useRef<HTMLInputElement>(null),
    start: useRef<HTMLInputElement>(null),
    end: useRef<HTMLInputElement>(null),
    place: useRef<HTMLInputElement>(null),
  };
  const [focus, setFocus] = useState<{ field: LabHourField; n: number }>({ field: "date", n: 0 });
  useEffect(() => fields[focus.field].current?.focus(), [focus]);

  const messages = { lab_hour_ended: copy.hasEnded, invalid_lab_hour: copy.refused };
  const save = useAction({
    mutationFn: () => (lab ? changeLabHour(sessionId, lab.id, labHourBody(inputs)) : addLabHour(sessionId, labHourBody(inputs))),
    messages,
    onSuccess: onSaved,
  });
  const remove = useAction({
    mutationFn: () => removeLabHour(sessionId, lab!.id),
    messages,
    onSuccess: () => onRemoved?.(),
  });
  const pending = save.isPending || remove.isPending;

  const refuse = (found: LabHourErrors) => {
    setErrors(found);
    const first = firstRefusedField(found);
    if (first) setFocus((prev) => ({ field: first, n: prev.n + 1 }));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    save.reset();
    remove.reset();
    const halfTyped: HalfTyped = {
      date: fields.date.current?.validity.badInput,
      start: fields.start.current?.validity.badInput,
      end: fields.end.current?.validity.badInput,
    };
    const found = checkLabHour(inputs, halfTyped);
    if (firstRefusedField(found)) {
      refuse(found);
      return;
    }
    save.mutate(undefined, {
      onError: (failure) => {
        if (stale(failure)) onStale();
        refuse(labHourRefusal(failure));
      },
    });
  };

  const change = (field: LabHourField, value: string) => {
    setInputs((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
    if (save.isError) save.reset();
    if (remove.isError) remove.reset();
  };

  const consequenceId = `${idPrefix}-consequence`;
  return (
    <form noValidate aria-labelledby={`${idPrefix}-title`} className={`${PANEL} mt-3 mb-2`} onSubmit={submit}>
      <h4 id={`${idPrefix}-title`} className="text-label text-ink">
        {lab ? copy.editTitle : copy.addTitle}
      </h4>
      <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-3">
        <TextField
          id={`${idPrefix}-date`}
          ref={fields.date}
          type="date"
          label={copy.date}
          value={inputs.date}
          error={errors.date}
          onChange={(event) => change("date", event.target.value)}
        />
        <TextField
          id={`${idPrefix}-start`}
          ref={fields.start}
          type="time"
          label={copy.start}
          value={inputs.start}
          error={errors.start}
          onChange={(event) => change("start", event.target.value)}
        />
        <TextField
          id={`${idPrefix}-end`}
          ref={fields.end}
          type="time"
          label={copy.end}
          value={inputs.end}
          error={errors.end}
          onChange={(event) => change("end", event.target.value)}
        />
      </div>
      <TextField
        id={`${idPrefix}-place`}
        ref={fields.place}
        label={copy.place}
        autoComplete="off"
        maxLength={PLACE_MAX}
        value={inputs.place}
        hint={copy.placeHint}
        error={errors.place}
        onChange={(event) => change("place", event.target.value)}
        className="w-full"
      />
      <p id={consequenceId} className="text-body-phone text-ink-secondary">
        {copy.consequence}
      </p>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Button type="submit" variant="primary" unavailable={pending} aria-describedby={consequenceId}>
          {save.isPending ? copy.saving : lab ? copy.saveEdit : copy.saveAdd}
        </Button>
        {lab ? (
          <Button
            type="button"
            unavailable={pending}
            aria-describedby={consequenceId}
            onClick={() => {
              if (pending) return;
              save.reset();
              remove.mutate(undefined, {
                onError: (failure) => {
                  if (stale(failure)) onStale();
                },
              });
            }}
          >
            {remove.isPending ? copy.removing : copy.remove}
          </Button>
        ) : null}
        <button
          type="button"
          className={LINK_BUTTON}
          onClick={() => {
            if (!pending) onCancel();
          }}
        >
          {copy.cancel}
        </button>
      </div>
      <ActionError message={save.errorMessage ?? remove.errorMessage} />
    </form>
  );
}
