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

import { classOverviewKey, endInRoom, type GameInRoom, type GameInsight, gameInsightKey, markInRoom } from "./api";
import { confirmLabel, IN_ROOM_DEFAULT, inRoomError, inRoomLine, inRoomMinutes, markedText, osloClock } from "./in-room";

const copy = nb.spillstyring.inRoom;
const studentCopy = nb.homes.student.inRoom;
const LINE = "text-body-phone text-ink lg:text-body";

/** After an «I rommet» command: Spillinnsikt is the answer; it and the Oversikt read again. */
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
 * «I rommet» in Spillstyring (Story 8.11, FR-36, UX-DR8, UX-DR52, EXPERIENCE.md → Spillstyring → I
 * rommet), for a Lecturer on a running game (`can_mark_in_room`). While a Labtime is on
 * (`lab_hour_ends_at`) the secondary «Marker som i rommet» opens the form in place; outside one it
 * is unavailable (`aria-disabled`) with «Kan bare brukes i en Labtime.» above it. The form: «Ventetid
 * i rommet» in whole minutes (10), the line naming the Labtime's end, the primary «Marker som i
 * rommet, 10 min» and «Avbryt». Focus moves to the field on open and back to the opener on
 * «Avbryt»; a value outside 2 to 120 is said under the field (the Ordrefelt error pattern) on
 * leaving it and on the press. Marked: «I rommet til 16:00. KI tar over etter 10 min uten ordre.»
 * with the secondary «Ikke i rommet lenger». A done action's result line replaces the form and takes
 * focus; any refusal is said inline and the button stays active.
 */
export function InRoomStyring({ data }: { data: GameInsight }) {
  const ids = useId();
  const store = useReread(data.game_id, data.class_session_id);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(String(IN_ROOM_DEFAULT));
  const [error, setError] = useState<string | undefined>(undefined);
  const [result, setResult] = useState({ text: "", n: 0 });
  const openerRef = useRef<HTMLButtonElement>(null);
  const fieldRef = useRef<HTMLInputElement>(null);
  const [focusField, setFocusField] = useState(0);
  useEffect(() => {
    if (focusField > 0) fieldRef.current?.focus();
  }, [focusField]);

  const marked = data.in_room ?? null;
  const labEnds = data.lab_hour_ends_at ?? null;
  const done = (line: string) => {
    setOpen(false);
    setResult((prev) => ({ text: line, n: prev.n + 1 }));
  };
  const marking = useAction({
    mutationFn: (minutes: number) => markInRoom(data.game_id, minutes),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (insight: GameInsight) => {
      store.set(insight);
      void store.reread();
      const until = insight.in_room?.until ?? labEnds;
      done(until ? copy.done(osloClock(until)) : copy.open);
    },
  });
  const ending = useAction({
    mutationFn: () => endInRoom(data.game_id),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (insight: GameInsight) => {
      store.set(insight);
      void store.reread();
      done(copy.ended);
    },
  });
  // The form closes for good when the game was marked meanwhile or the Labtime has ended.
  const shown = open && !marked && labEnds !== null;

  const quiet = () => {
    marking.reset();
    ending.reset();
    setResult((prev) => ({ text: "", n: prev.n }));
  };
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (marking.isPending) return;
    marking.reset();
    const minutes = inRoomMinutes(text);
    if (minutes === null) {
      setError(copy.error);
      setFocusField((n) => n + 1);
      return;
    }
    marking.mutate(minutes, {
      onError: (failure) => {
        if (errorCode(failure) === "minutes_out_of_range") {
          marking.reset();
          setError(copy.error);
          setFocusField((n) => n + 1);
          return;
        }
        void store.reread();
      },
    });
  };

  const lineId = `${ids}-line`;
  const unavailableId = `${ids}-unavailable`;
  return (
    <div className="mt-3 flex flex-col items-start gap-3 border-b border-hairline pb-4" data-spillstyring-in-room="">
      {marked ? (
        <>
          <p className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body" data-in-room-marked="">
            {markedText(marked)}
          </p>
          <Button
            data-in-room-end=""
            className="w-full lg:w-auto"
            unavailable={ending.isPending}
            onClick={() => {
              quiet();
              ending.mutate();
            }}
          >
            {copy.end}
          </Button>
        </>
      ) : shown ? (
        <form
          noValidate
          aria-label={copy.open}
          data-in-room-form=""
          className="flex w-full max-w-xl flex-col items-start gap-4 rounded-sm border border-axis bg-paper px-4 py-4"
          onSubmit={submit}
        >
          <TextField
            id={`${ids}-minutes`}
            ref={fieldRef}
            label={copy.field}
            hint={copy.help}
            inputMode="numeric"
            autoComplete="off"
            className="w-full max-w-48"
            value={text}
            errorAlert
            error={error}
            onChange={(event) => {
              setText(event.target.value);
              setError(undefined);
              if (marking.isError) marking.reset();
            }}
            onBlur={() => setError(inRoomError(text))}
          />
          <p id={lineId} className="text-body-phone text-ink lg:text-body">
            {copy.consequence(osloClock(labEnds ?? ""))}
          </p>
          <div className="flex w-full flex-col items-stretch gap-x-6 gap-y-2 lg:flex-row lg:items-center">
            <Button
              type="submit"
              variant="primary"
              data-in-room-confirm=""
              className="w-full lg:w-auto"
              aria-describedby={lineId}
              unavailable={marking.isPending}
            >
              {confirmLabel(text)}
            </Button>
            <button
              type="button"
              data-in-room-cancel=""
              className={cn(LINK_BUTTON, "self-start")}
              onClick={() => {
                if (marking.isPending) return;
                setOpen(false);
                requestAnimationFrame(() => openerRef.current?.focus());
              }}
            >
              {copy.cancel}
            </button>
          </div>
          {errorCode(marking.error) === "minutes_out_of_range" ? null : <ActionError message={marking.errorMessage} />}
        </form>
      ) : (
        <>
          {labEnds === null ? (
            <p id={unavailableId} className="text-caption text-ink-secondary" data-in-room-unavailable="">
              {copy.onlyInLabHour}
            </p>
          ) : null}
          <Button
            ref={openerRef}
            data-in-room-open=""
            className="w-full lg:w-auto"
            unavailable={labEnds === null}
            aria-describedby={labEnds === null ? unavailableId : undefined}
            onClick={() => {
              quiet();
              setText(String(IN_ROOM_DEFAULT));
              setError(undefined);
              setOpen(true);
              setFocusField((n) => n + 1);
            }}
          >
            {copy.open}
          </Button>
        </>
      )}
      <ActionError message={ending.errorMessage} />
      <InRoomResult text={result.text} n={result.n} />
    </div>
  );
}

/** The result line that replaces a closed form and takes focus (`tabindex="-1"`, `role="status"`),
 * as the Pause's in the same block. */
function InRoomResult({ text, n }: { text: string; n: number }) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (n > 0) ref.current?.focus();
  }, [n]);
  return (
    <p
      ref={ref}
      tabIndex={-1}
      role="status"
      data-in-room-result=""
      className={cn("text-body-phone text-ink focus:outline-none lg:text-body", !text && "sr-only")}
    >
      {text}
    </p>
  );
}

/**
 * The «I rommet» line above Setestatus on Spill (Story 8.11, FR-36, UX-DR62): «I rommet til kl.
 * 16:00. En KI-spiller tar setet etter 10 min uten ordre.», with the reader's own minutes, for every
 * Student of the game. A polite live region that is always there and is filled after it is drawn,
 * so the line is read when the mark starts (and when the page opens with it). When the mark ends
 * while the page is open, «Spillet er ikke i rommet lenger. …» is read, and not shown.
 */
export function InRoomLine({ inRoom, className }: { inRoom: GameInRoom | null | undefined; className?: string }) {
  const text = inRoomLine(inRoom);
  const [said, setSaid] = useState<{ text: string; ended: boolean }>({ text: "", ended: false });
  const seen = useRef(false);
  useEffect(() => {
    if (text) {
      seen.current = true;
      setSaid({ text, ended: false });
    } else if (seen.current) {
      seen.current = false;
      setSaid({ text: studentCopy.ended, ended: true });
    } else {
      setSaid({ text: "", ended: false });
    }
  }, [text]);
  const state = said.text ? (said.ended ? "ended" : "on") : "";
  return (
    <div aria-live="polite" data-in-room-line={state} className={state === "on" ? className : undefined}>
      {said.text ? <p className={cn(LINE, "max-w-md font-semibold", said.ended && "sr-only")}>{said.text}</p> : null}
    </div>
  );
}
