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

import { classOverviewKey, type GameInsight, gameInsightKey, takeOverSeat } from "./api";
import { seatsUpstreamFirst } from "./insight";

const copy = nb.spillstyring;

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
 * Spillstyring on Spillinnsikt (Story 8.5, FR-37, UX-DR52, EXPERIENCE.md → Spillstyring): under the
 * four Seats while the game runs, one row per Student-held Seat (Fabrikk first) with its
 * consequence and «Sett inn KI-spiller for …». The api decides which Seats and from when
 * (`takeover`, AD-10). A row stays after its press, so its result line can be read; a game not
 * started or finished shows no block. The same for Lecturers and Assistant lecturers: the per-Seat
 * Takeover is the only Spillstyring action so far.
 */
export function Spillstyring({ data }: { data: GameInsight }) {
  const id = useId();
  // The Seats pressed here, with the name the row had then: the row and its result line stay.
  const [pressed, setPressed] = useState<ReadonlyMap<Role, string>>(new Map());
  if (data.status !== "running" && data.status !== "waiting") return null;
  const rows = seatsUpstreamFirst(data).filter((seat) => seat.takeover != null || pressed.has(seat.role));
  if (rows.length === 0) return null;
  return (
    <section aria-labelledby={id} className="mt-8" data-spillstyring="">
      <h2 id={id} className="text-headline text-ink">
        {copy.title}
      </h2>
      <ul className="mt-3 flex flex-col gap-4">
        {rows.map((seat) => {
          const name = pressed.get(seat.role) ?? seat.name ?? roleName(seat.role);
          return (
            <li key={seat.role} data-role={seat.role} className="flex min-w-0 flex-col gap-2 border-b border-hairline pb-4">
              <p className="text-label text-ink [overflow-wrap:anywhere]">{copy.seat(roleName(seat.role), name)}</p>
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
    </section>
  );
}
