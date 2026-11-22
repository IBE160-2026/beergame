"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { errorCode, useAction } from "@/lib/api/mutation";
import { roleName } from "@/modules/sessions/sessions";

import {
  classOverviewKey,
  fillWaitedForSeats,
  type GameInsight,
  gameInsightKey,
  startGameAsLecturer,
  startGamesKey,
  takeOverSeat,
  waitedForSeatsKey,
} from "./api";
import { fillFailed, filledText, leftOutText, namesText, seatName } from "./fill-seats";
import { InRoomStyring } from "./in-room-view";
import { seatsUpstreamFirst } from "./insight";
import { insightPauseText, type PauseMode, PauseResult, StaffPauseForm, useEndPause } from "./staff-pause";
import { type StartResult, startedFirst, startResultText } from "./start-games";

const copy = nb.spillstyring;
const pauseCopy = nb.spillstyring.pause;
const startCopy = nb.spillstyring.start;
const fillCopy = nb.spillstyring.fill;

type Role = components["schemas"]["Role"];
type From = "this_week" | "next_week";

/** Who acted first, from a `takeover_exists` refusal (Story 8.5): its kind; the name is read from
 * the view read again (`mark_by`), never from the error. */
export type ActedBy = "staff" | "student" | "system";

export function actedKind(error: unknown): ActedBy | null {
  if (!(error instanceof ApiRequestError) || error.code !== "takeover_exists") return null;
  const by = error.fields.acted_by as { kind?: unknown } | undefined;
  return by?.kind === "staff" || by?.kind === "student" || by?.kind === "system" ? by.kind : "system";
}

/** The line naming who put an AI player in first: «Sara har allerede satt inn en KI-spiller.» */
export function takenText(kind: ActedBy, name: string | null | undefined): string {
  if (kind === "system") return copy.takenBySystem;
  return name ? copy.taken(name) : copy.takenByUnknown;
}

/** What a press came to: put in for the Student named then, or someone came first. */
export type TakeoverResult = { kind: "done"; name: string } | { kind: "taken"; by: ActedBy };

/** The result line: «KI-spiller satt inn for Jonas.» or who came first, by the name the view read
 * again gives (`actedBy`). */
export function resultText(result: TakeoverResult, actedBy: string | null | undefined): string {
  return result.kind === "done" ? copy.done(result.name) : takenText(result.by, actedBy);
}

/** The consequence above «Sett inn KI-spiller for Jonas»: from this Uke, or from the next once
 * Jonas has ordered this Uke. */
export function consequenceText(from: From, name: string): string {
  return from === "this_week" ? copy.thisWeek(name) : copy.nextWeek(name);
}

/**
 * One «Sett inn KI-spiller for Jonas» (Story 8.5, FR-37, UX-DR52, UX-DR76): a secondary button, at
 * least 44 px and full width below 1024 px; one press, no dialog. `consequence`, when given, stands
 * directly above it. After the api commits, «KI-spiller satt inn for Jonas.» replaces the button
 * and takes focus (`tabindex="-1"`, `role="status"`). When someone put an AI player in first
 * (`takeover_exists`), the line naming them replaces it the same way, the name read from the view
 * read again (`actedBy`); any other refusal is said inline and the button stays active. Spillinnsikt
 * and the Oversikt are read again either way.
 */
export function TakeoverAction({
  gameId,
  sessionId,
  role,
  name,
  consequence,
  actedBy,
  onPress,
  onResult,
}: {
  gameId: string;
  sessionId: string;
  role: Role;
  name: string;
  consequence?: string | null;
  actedBy?: string | null;
  onPress?: () => void;
  /** When given, the caller shows the result line (the Varselbånd moves on to another game). */
  onResult?: (result: TakeoverResult) => void;
}) {
  const queryClient = useQueryClient();
  const [result, setOwnResult] = useState<TakeoverResult | null>(null);
  const setResult = (found: TakeoverResult) => (onResult ? onResult(found) : setOwnResult(found));
  // The name as it was at the press: once an AI player holds the Seat the view no longer names it.
  const named = useRef(name);
  const lineRef = useRef<HTMLParagraphElement>(null);
  const focusLine = useRef(false);
  const reread = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: gameInsightKey(gameId) }),
      queryClient.invalidateQueries({ queryKey: classOverviewKey(sessionId) }),
    ]);
  const taking = useAction({
    mutationFn: () => takeOverSeat(gameId, role),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (insight: GameInsight) => {
      queryClient.setQueryData(gameInsightKey(gameId), insight);
      void reread();
      focusLine.current = true;
      setResult({ kind: "done", name: named.current });
    },
  });
  useEffect(() => {
    if (focusLine.current && lineRef.current) {
      focusLine.current = false;
      lineRef.current.focus();
    }
  });
  if (result) {
    return (
      <p
        ref={lineRef}
        tabIndex={-1}
        role="status"
        data-takeover-result={result.kind}
        className="text-body-phone text-ink focus:outline-none lg:text-body"
      >
        {resultText(result, actedBy)}
      </p>
    );
  }
  return (
    <div className="flex flex-col items-start gap-2">
      {consequence ? (
        <p className="text-caption text-ink-secondary" data-takeover-consequence="">
          {consequence}
        </p>
      ) : null}
      <Button
        data-takeover={role}
        className="w-full lg:w-auto"
        unavailable={taking.isPending}
        onClick={() => {
          named.current = name;
          onPress?.();
          taking.mutate(undefined, {
            onError: (error) => {
              const by = actedKind(error);
              // Who came first is named from the view read again: the line waits for that read.
              void reread().then(() => {
                if (by === null) return;
                focusLine.current = true;
                setResult({ kind: "taken", by });
              });
            },
          });
        }}
      >
        {copy.takeover(name)}
      </Button>
      {errorCode(taking.error) === "takeover_exists" ? null : <ActionError message={taking.errorMessage} />}
    </div>
  );
}

/**
 * Spillstyring on Spillinnsikt (Stories 8.5 and 8.7, FR-37, FR-89, UX-DR52, EXPERIENCE.md →
 * Spillstyring): under the four Seats while the game runs. For a Lecturer of the Class (`can_pause`)
 * first the Pause: «Pause spillet» on a game that is not paused, or the paused line «Pause siden
 * ma. 14:10, satt av Sara.» with «Endre avtalt tid» and «Avslutt pausen»; their form opens in place,
 * and the result line replaces it and takes focus. Then «I rommet» for a Lecturer (Story 8.11,
 * `InRoomStyring`). Then one row per Student-held Seat (Fabrikk
 * first) with its consequence and «Sett inn KI-spiller for …», which Assistant lecturers have too.
 * The api decides which Seats and from when (`takeover`, AD-10). A row stays after its press, so its
 * result line can be read; a finished game shows no block; a paused one keeps it. A game not
 * started shows the block only with «Start spillet» for a Lecturer (Story 8.10, `can_start`).
 */
export function Spillstyring({ data }: { data: GameInsight }) {
  const id = useId();
  // The Seats pressed here, with the name the row had then: the row and its result line stay.
  const [pressed, setPressed] = useState<ReadonlyMap<Role, string>>(new Map());
  // «Start spillet»'s result line stays once the game runs, above the block's other actions.
  const [started, setStarted] = useState<StartResult | null>(null);
  // «2 KI-spillere satt inn.» stays once the game no longer waits for those Seats (Story 8.12),
  // until it waits for other Seats (a later Uke): then the button is offered again.
  const [filled, setFilled] = useState<number | null>(null);
  const waitedIds = data.waited_for.map((seat) => seat.seat_id).join(" ");
  const [shownWaits, setShownWaits] = useState(waitedIds);
  if (waitedIds !== shownWaits) {
    setShownWaits(waitedIds);
    if (waitedIds !== "") setFilled(null);
  }
  const startShown = data.can_start || started !== null;
  // A paused game still runs: the staff's per-Seat action stays (Story 8.6).
  const running = data.status === "running" || data.status === "waiting" || data.status === "paused";
  const rows = running ? seatsUpstreamFirst(data).filter((seat) => seat.takeover != null || pressed.has(seat.role)) : [];
  const pauseShown = running && data.can_pause;
  const inRoomShown = running && data.can_mark_in_room;
  const fillShown = running && (data.waited_for.length > 0 || data.left_out.length > 0 || filled !== null);
  if (!startShown && !pauseShown && !inRoomShown && !fillShown && rows.length === 0) return null;
  return (
    <section aria-labelledby={id} className="mt-8" data-spillstyring="">
      <h2 id={id} className="text-label text-ink">
        {copy.title}
      </h2>
      {startShown ? <StartStyring data={data} result={started} onResult={setStarted} /> : null}
      {pauseShown ? <PauseStyring data={data} /> : null}
      {/* «I rommet» (Story 8.11): a Lecturer, while the game runs. */}
      {inRoomShown ? <InRoomStyring data={data} /> : null}
      {/* Every waited-for Seat of this game in one press (Story 8.12): a Lecturer. */}
      {fillShown ? <FillStyring data={data} result={filled} onResult={setFilled} /> : null}
      {rows.length > 0 ? (
        <ul className="mt-3 flex flex-col gap-4">
          {rows.map((seat) => {
            const name = pressed.get(seat.role) ?? seat.name ?? roleName(seat.role);
            return (
              <li key={seat.role} data-role={seat.role} className="flex min-w-0 flex-col gap-2 border-b border-hairline pb-4">
                <p className="text-label text-ink [overflow-wrap:anywhere]">{copy.seat(roleName(seat.role), name)}</p>
                {/* Tilrettelegging, for the Lecturer only: the api sets it for no one else (Story 8.9). */}
                {seat.extra_time ? (
                  <p className="text-caption text-ink-secondary" data-extra-time="">
                    {copy.extraTime(name)}
                  </p>
                ) : null}
                <TakeoverAction
                  gameId={data.game_id}
                  sessionId={data.class_session_id}
                  role={seat.role}
                  name={name}
                  consequence={seat.takeover ? consequenceText(seat.takeover, name) : null}
                  actedBy={seat.mark_by}
                  onPress={() => setPressed((before) => new Map(before).set(seat.role, name))}
                />
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}

/**
 * «Start spillet» in Spillstyring (Story 8.10, FR-22, UX-DR52, EXPERIENCE.md → Spillstyring →
 * Start), for a Lecturer on a game that may start (`can_start`): the consequence directly above the
 * primary button, full width below 1024 px; one press, no dialog. After the api commits, «Spillet er
 * startet.» replaces it and takes focus (`tabindex="-1"`, `role="status"`). When someone started it
 * first (`game_already_started`), the line naming them replaces it the same way, the name read from
 * the view read again (`started_by`); any other refusal is said inline and the button stays active.
 */
function StartStyring({
  data,
  result,
  onResult,
}: {
  data: GameInsight;
  result: StartResult | null;
  onResult: (result: StartResult) => void;
}) {
  const queryClient = useQueryClient();
  const lineId = useId();
  const lineRef = useRef<HTMLParagraphElement>(null);
  const reread = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: gameInsightKey(data.game_id) }),
      queryClient.invalidateQueries({ queryKey: classOverviewKey(data.class_session_id) }),
      queryClient.invalidateQueries({ queryKey: startGamesKey(data.class_session_id) }),
    ]);
  const starting = useAction({
    mutationFn: () => startGameAsLecturer(data.game_id),
    messages: startCopy.refusals,
    fallback: startCopy.failed,
    onSuccess: (insight: GameInsight) => {
      queryClient.setQueryData(gameInsightKey(data.game_id), insight);
      void reread();
      onResult({ kind: "done" });
    },
  });
  // The result line takes focus when it comes, also when the block was redrawn meanwhile (the
  // view read again after a lost race may hide «Start spillet» before the line is set).
  useEffect(() => {
    if (result) lineRef.current?.focus();
  }, [result]);
  if (result) {
    return (
      <p
        ref={lineRef}
        tabIndex={-1}
        role="status"
        data-start-result={result.kind}
        className="mt-3 border-b border-hairline pb-4 text-body-phone text-ink [overflow-wrap:anywhere] focus:outline-none lg:text-body"
      >
        {startResultText(result, data.started_by)}
      </p>
    );
  }
  return (
    <div className="mt-3 flex flex-col items-start gap-3 border-b border-hairline pb-4" data-spillstyring-start="">
      <p id={lineId} className="text-body-phone text-ink lg:text-body" data-start-consequence="">
        {startCopy.consequence}
      </p>
      <Button
        variant="primary"
        data-start-game=""
        className="w-full lg:w-auto"
        aria-describedby={lineId}
        unavailable={starting.isPending}
        onClick={() =>
          starting.mutate(undefined, {
            onError: (error) => {
              if (!startedFirst(error)) return;
              // Who started it first is named from the view read again: the line waits for it.
              void reread().then(() => onResult({ kind: "first" }));
            },
          })
        }
      >
        {startCopy.button}
      </Button>
      {startedFirst(starting.error) ? null : <ActionError message={starting.errorMessage} />}
    </div>
  );
}

/**
 * «Sett inn KI-spiller i alle seter som blir ventet på (2)» in Spillstyring (Story 8.12, FR-37,
 * UX-DR52, EXPERIENCE.md → Spillstyring → Fill waited-for Seats), for a Lecturer: the consequence
 * directly above the secondary button, full width below 1024 px, then «Ikke med (tilrettelegging):
 * Jonas» for the Seats the api left out; one press, no dialog. The press posts the Seats the api
 * listed; the api skips any that ordered or were taken meanwhile. «2 KI-spillere satt inn.», with
 * the real count, replaces the button and takes focus (`tabindex="-1"`, `role="status"`); a failure
 * is said inline and the button stays active.
 */
function FillStyring({
  data,
  result,
  onResult,
}: {
  data: GameInsight;
  result: number | null;
  onResult: (inserted: number) => void;
}) {
  const queryClient = useQueryClient();
  const lineId = useId();
  const lineRef = useRef<HTMLParagraphElement>(null);
  const seats = data.waited_for;
  const leftOut = leftOutText(data.left_out);
  const filling = useAction({
    mutationFn: async () => {
      const answer = await fillWaitedForSeats(
        data.class_session_id,
        seats.map((seat) => seat.seat_id),
      );
      if (fillFailed(answer)) throw new Error("fill failed");
      return answer;
    },
    fallback: fillCopy.failed,
    onSuccess: (answer) => {
      onResult(answer.inserted);
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: gameInsightKey(data.game_id) }),
        queryClient.invalidateQueries({ queryKey: classOverviewKey(data.class_session_id) }),
        queryClient.invalidateQueries({ queryKey: waitedForSeatsKey(data.class_session_id) }),
      ]);
    },
  });
  useEffect(() => {
    if (result !== null) lineRef.current?.focus();
  }, [result]);
  if (result !== null) {
    return (
      <p
        ref={lineRef}
        tabIndex={-1}
        role="status"
        data-fill-result=""
        className="mt-3 border-b border-hairline pb-4 text-body-phone text-ink tabular-nums lining-nums focus:outline-none lg:text-body"
      >
        {filledText(result)}
      </p>
    );
  }
  return (
    <div className="mt-3 flex flex-col items-start gap-2 border-b border-hairline pb-4" data-spillstyring-fill="">
      {seats.length > 0 ? (
        <>
          <p id={lineId} className="text-caption text-ink-secondary [overflow-wrap:anywhere]" data-fill-consequence="">
            {fillCopy.consequence(namesText(seats.map(seatName)))}
          </p>
          <Button
            data-fill-seats=""
            className="w-full lg:w-auto"
            aria-describedby={lineId}
            unavailable={filling.isPending}
            onClick={() => filling.mutate(undefined)}
          >
            {fillCopy.button(seats.length)}
          </Button>
        </>
      ) : null}
      {leftOut ? (
        <p className="text-caption text-ink-secondary [overflow-wrap:anywhere]" data-fill-left-out="">
          {leftOut}
        </p>
      ) : null}
      <ActionError message={filling.errorMessage} />
    </div>
  );
}

/**
 * The Lecturer's Pause in Spillstyring (Story 8.7): one in-place form at a time. «Pause spillet»,
 * «Endre avtalt tid» and «Avbryt» move focus as EXPERIENCE.md asks (the form's first field; back to
 * the opener); a done action's result line replaces the form and takes focus.
 */
function PauseStyring({ data }: { data: GameInsight }) {
  const [open, setOpen] = useState<PauseMode | null>(null);
  const [result, setResult] = useState({ text: "", n: 0 });
  const openerRef = useRef<HTMLButtonElement>(null);
  const done = (text: string) => {
    setOpen(null);
    setResult((prev) => ({ text, n: prev.n + 1 }));
  };
  const ending = useEndPause(data.game_id, data.class_session_id, done);
  const paused = data.pause ?? null;
  // A form for a state that has gone (the game was paused or resumed meanwhile) closes.
  const shown = open === "pause" ? (paused ? null : open) : open === "change" ? (paused ? open : null) : null;
  const opener = (mode: PauseMode) => () => {
    ending.reset();
    setResult((prev) => ({ text: "", n: prev.n }));
    setOpen(mode);
  };
  const cancel = () => {
    setOpen(null);
    requestAnimationFrame(() => openerRef.current?.focus());
  };
  return (
    <div className="mt-3 flex flex-col items-start gap-3 border-b border-hairline pb-4" data-spillstyring-pause="">
      {paused ? (
        <p className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body" data-insight-pause="">
          {insightPauseText(paused)}
        </p>
      ) : null}
      {shown ? (
        <StaffPauseForm
          gameId={data.game_id}
          sessionId={data.class_session_id}
          mode={shown}
          resumeAt={paused?.resume_at ?? null}
          playDeadline={data.play_deadline}
          now={() => Date.now()}
          onCancel={cancel}
          onDone={done}
        />
      ) : paused ? (
        <div className="flex w-full flex-col items-stretch gap-3 lg:flex-row lg:items-center">
          <Button ref={openerRef} data-pause-change="" className="w-full lg:w-auto" onClick={opener("change")}>
            {pauseCopy.change}
          </Button>
          <Button
            data-pause-end=""
            className="w-full lg:w-auto"
            unavailable={ending.isPending}
            onClick={() => {
              setResult((prev) => ({ text: "", n: prev.n }));
              ending.mutate();
            }}
          >
            {pauseCopy.end}
          </Button>
        </div>
      ) : (
        <Button ref={openerRef} data-pause-open="" className="w-full lg:w-auto" onClick={opener("pause")}>
          {pauseCopy.open}
        </Button>
      )}
      <ActionError message={ending.errorMessage} />
      <PauseResult text={result.text} n={result.n} />
    </div>
  );
}
