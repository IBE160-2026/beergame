"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { osloDayAndTime } from "@/modules/sessions/dates";

import {
  completeStep,
  type Debrief,
  type Group,
  INDIVIDUAL_STEP,
  joinDebrief,
  lockedLine,
  moveOn,
  myDebriefKey,
  waitingFor,
} from "./api";

const copy = nb.debriefEntry.group;
const LINE = "text-body-phone lg:text-body";

/** The step heading the page moves focus to once the Student has joined (`debrief-page.tsx`). */
export const STEP_HEADING_ID = "debrief-step";

function useStore(debrief: Debrief) {
  const queryClient = useQueryClient();
  return (next: Debrief) => queryClient.setQueryData(myDebriefKey(debrief.class_session_id), next);
}

/**
 * «Bli med i Gruppedebriefen» (Story 9.11, FR-43): what a Student of the game sees while a Group
 * debrief of it is under way that they have not joined. Joining is the press; nothing joins on its
 * own. Once joined the steps follow and the page moves focus to step 1's heading.
 */
export function GroupJoin({ debrief }: { debrief: Debrief }) {
  const store = useStore(debrief);
  const join = useAction({
    mutationFn: () => joinDebrief(debrief.id),
    messages: { not_group: copy.notGroup },
    fallback: copy.joinFailed,
    onSuccess: store,
  });
  return (
    <section aria-labelledby="debrief-group-join" data-group-join="" className="mt-8 max-w-md border-t border-axis pt-4">
      <h2 id="debrief-group-join" className="text-headline text-ink">
        {copy.title}
      </h2>
      <p className={`${LINE} mt-2 text-ink`}>{copy.joinLead}</p>
      <div className="mt-4 flex flex-col items-start gap-2">
        <Button variant="primary" unavailable={join.isPending} onClick={() => join.mutate()}>
          {copy.join}
        </Button>
        <ActionError message={join.errorMessage} />
      </div>
    </section>
  );
}

/**
 * Says politely when the shared step moves (Story 9.11, UX-DR31): «Alle har sendt. Avsløringen er
 * åpen.» when step 2 opens because everyone has sent, else the step the group is on (the opener
 * moved it on). Never on the first read.
 */
export function GroupAnnouncer({ group }: { group: Group }) {
  const [said, setSaid] = useState("");
  const last = useRef(group.step);
  useEffect(() => {
    if (group.step === last.current) return;
    last.current = group.step;
    const everyoneSent = group.members.length > 0 && group.members.every((m) => m.sent);
    setSaid(
      group.step === 2 && everyoneSent ? copy.unlocked : group.step >= INDIVIDUAL_STEP ? copy.alone : copy.moved(group.step),
    );
  }, [group.step, group.members]);
  return (
    <p role="status" data-group-announce="" className="sr-only">
      {said}
    </p>
  );
}

/**
 * The group's line under the shared step the pointer is on (Story 9.11, FR-43, UX-DR31): on step
 * 1 the time guide while writing, then who has sent and who writes (names read now, never what
 * they wrote); on steps 2 and 3 «Ferdig med steget», then whom the group waits for. The opener
 * also gets «Gå videre for alle» with the time it becomes possible; a press before then says it
 * again (409 `too_early`). A Student who has not sent while the group is further on is told so.
 */
export function GroupStepBar({ debrief, group, sent }: { debrief: Debrief; group: Group; sent: boolean }) {
  const store = useStore(debrief);
  const finish = useAction({
    mutationFn: () => completeStep(debrief.id, group.step),
    fallback: copy.failed,
    onSuccess: store,
  });
  const move = useAction({
    mutationFn: () => moveOn(debrief.id),
    fallback: copy.failed,
    onSuccess: store,
  });
  const me = group.members.find((m) => m.you);
  const early =
    move.error instanceof ApiRequestError && move.error.code === "too_early" && typeof move.error.fields.available_at === "string"
      ? copy.tooEarly(osloDayAndTime(move.error.fields.available_at).time)
      : move.errorMessage;
  let line: string | null = null;
  if (!sent) line = group.step > 1 ? copy.behind(group.step) : copy.timeGuide;
  else if (group.step === 1) line = lockedLine(group.members, copy);
  else if (me?.done) {
    const waiting = waitingFor(group.members, copy);
    line = waiting ? copy.waiting(waiting) : null;
  }
  const canFinish = sent && group.step > 1 && group.step < INDIVIDUAL_STEP && !me?.done;
  const canMove = group.opener && group.step < INDIVIDUAL_STEP && (sent || group.step === 1);
  if (!line && !canFinish && !canMove) return null;
  return (
    <div data-group-bar={group.step} className="mt-6 flex max-w-md flex-col items-start gap-3 border-l-2 border-axis pl-3">
      {line ? (
        <p data-group-line="" className={`${LINE} text-ink`}>
          {line}
        </p>
      ) : null}
      {canFinish ? (
        <>
          <Button unavailable={finish.isPending} onClick={() => finish.mutate()}>
            {copy.done}
          </Button>
          <ActionError message={finish.errorMessage} />
        </>
      ) : null}
      {canMove ? (
        <>
          {group.move_on_at ? <p className="text-caption text-ink-secondary">{copy.moveOnAt(osloDayAndTime(group.move_on_at).time)}</p> : null}
          <Button unavailable={move.isPending} onClick={() => move.mutate()}>
            {copy.moveOn}
          </Button>
          <ActionError message={early} />
        </>
      ) : null}
    </div>
  );
}
