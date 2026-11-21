"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { LINK_BUTTON } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { acceptTime, type MyGame, myGameKey, proposeTime } from "./api";
import {
  checkProposal,
  EMPTY_PROPOSAL,
  type ProposalErrors,
  type ProposalField,
  proposalAt,
  proposalLines,
  refusedRange,
  shownProposal,
  type TimeProposal,
} from "./time-proposal";

const copy = nb.games.timeProposal;
const LINE = "text-body-phone text-ink lg:text-body";
const PANEL = "mt-3 flex w-full flex-col items-start gap-4 rounded-sm border border-axis px-4 py-4";

/** After a proposal or an acceptance: the answer is the game as it now stands; Hjem reads again. */
function useStore(gameId: string) {
  const queryClient = useQueryClient();
  return {
    set: (game: MyGame) => {
      queryClient.setQueryData(myGameKey(gameId), game);
      void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
    },
    reread: () => {
      void queryClient.invalidateQueries({
        queryKey: myGameKey(gameId),
        exact: true,
      });
      void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
    },
  };
}

/**
 * The scheduling aid (Story 6.19, FR-22): the game's open proposal of a time to play, who
 * proposed it by name and who accepted, and «Godta tidspunktet» for a Student who may accept it,
 * one press. With `playDeadline` (Hjem only) also «Foreslå tidspunkt», which opens a form in place
 * with a date and a time field and no text field. A time is never free text, and it never governs
 * the wait before a KI-spiller may be put in (AD-20). `now` is the server's clock (ms): a time that
 * has passed goes at once. `onFormOpen` tells Hjem the form is open, so its primary steps back.
 */
export function TimeProposalBlock({
  game,
  now,
  playDeadline = null,
  onFormOpen,
  className,
}: {
  game: MyGame;
  now: number;
  /** The Class session's Play deadline: the latest time to propose. Without it no form is offered. */
  playDeadline?: string | null;
  onFormOpen?: (open: boolean) => void;
  className?: string;
}) {
  const ids = useId();
  const proposal = shownProposal(game.time_proposal, now);
  const seated = game.seats.some((seat) => seat.mine);
  // After the Play deadline no time is left to propose: the control goes (the api refuses too).
  const canPropose = playDeadline !== null && Date.parse(playDeadline) > now && seated && game.status !== "finished";
  const [open, setOpenState] = useState(false);
  const [result, setResult] = useState<{ text: string; n: number }>({
    text: "",
    n: 0,
  });
  const openerRef = useRef<HTMLButtonElement>(null);
  const resultRef = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (result.n > 0) resultRef.current?.focus();
  }, [result]);
  const setOpen = (next: boolean) => setOpenState(next);
  // Hjem hears whether a form is shown: also when the game finishes under an open form, or the
  // block goes, so its primary never stays stepped back.
  const formShown = open && canPropose;
  const told = useRef(onFormOpen);
  useEffect(() => {
    told.current = onFormOpen;
  });
  useEffect(() => {
    told.current?.(formShown);
    return () => told.current?.(false);
  }, [formShown]);
  // Kept here, not in the line: a refused press (the proposal was replaced or has passed) reads the
  // game again, which takes the line away, and its reason must stay.
  const store = useStore(game.id);
  const accepting = useAction({
    mutationFn: (proposalId: string) => acceptTime(game.id, proposalId),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: store.set,
  });
  if (!proposal && !canPropose && !accepting.errorMessage) return null;
  return (
    <div className={cn("flex flex-col items-start", className)} data-time-proposal="">
      {proposal ? (
        <ProposalLine
          proposal={proposal}
          pending={accepting.isPending}
          onAccept={() => accepting.mutate(proposal.id, { onError: store.reread })}
        />
      ) : null}
      <ActionError message={accepting.errorMessage} />
      {canPropose && !open ? (
        <button
          ref={openerRef}
          type="button"
          className={LINK_BUTTON}
          onClick={() => {
            setResult((prev) => ({ text: "", n: prev.n }));
            setOpen(true);
          }}
        >
          {copy.open}
        </button>
      ) : null}
      {canPropose && open ? (
        <ProposalForm
          idPrefix={ids}
          gameId={game.id}
          now={now}
          playDeadline={playDeadline}
          replaces={proposal !== null}
          onCancel={() => {
            setOpen(false);
            // After the form unmounts and «Foreslå tidspunkt» is back, focus it.
            requestAnimationFrame(() => openerRef.current?.focus());
          }}
          onSent={() => {
            setOpen(false);
            setResult((prev) => ({ text: copy.sent, n: prev.n + 1 }));
          }}
        />
      ) : null}
      <p ref={resultRef} tabIndex={-1} role="status" className={cn(LINE, "focus:outline-none")}>
        {result.text}
      </p>
    </div>
  );
}

/** «Kari Nordmann foreslår å spille to. 26. nov. kl. 14:15.», who accepted, and «Godta
 * tidspunktet» while the reader may accept it. */
function ProposalLine({
  proposal,
  pending,
  onAccept,
}: {
  proposal: TimeProposal;
  pending: boolean;
  onAccept: () => void;
}) {
  const lines = proposalLines(proposal);
  return (
    <div className="flex flex-col items-start gap-1">
      <p className={LINE}>{lines.proposed}</p>
      <p className="text-body-phone text-ink-secondary lg:text-body">{lines.accepted}</p>
      {proposal.can_accept ? (
        <Button className="mt-2" unavailable={pending} onClick={onAccept}>
          {pending ? copy.accepting : copy.accept}
        </Button>
      ) : null}
    </div>
  );
}

/** The in-place form: «Dato» and «Klokkeslett», the consequence, the primary «Send forslaget til
 * gruppen» and «Avbryt». Focus moves to «Dato» on open and to the first refused field. */
function ProposalForm({
  idPrefix,
  gameId,
  now,
  playDeadline,
  replaces,
  onCancel,
  onSent,
}: {
  idPrefix: string;
  gameId: string;
  now: number;
  playDeadline: string;
  replaces: boolean;
  onCancel: () => void;
  onSent: () => void;
}) {
  const store = useStore(gameId);
  const [inputs, setInputs] = useState(EMPTY_PROPOSAL);
  const [errors, setErrors] = useState<ProposalErrors>({});
  const fields = {
    date: useRef<HTMLInputElement>(null),
    time: useRef<HTMLInputElement>(null),
  };
  const [focus, setFocus] = useState<{ field: ProposalField; n: number }>({
    field: "date",
    n: 0,
  });
  useEffect(() => fields[focus.field].current?.focus(), [focus]);

  const send = useAction({
    mutationFn: () => proposeTime(gameId, proposalAt(inputs)),
    messages: copy.refusals,
    fallback: copy.failed,
    onSuccess: (game: MyGame) => {
      store.set(game);
      onSent();
    },
  });

  const refuse = (found: ProposalErrors) => {
    setErrors(found);
    const first = (["date", "time"] as const).find((field) => found[field]);
    if (first) setFocus((prev) => ({ field: first, n: prev.n + 1 }));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (send.isPending) return;
    send.reset();
    const found = checkProposal(inputs, now, playDeadline, {
      date: fields.date.current?.validity.badInput,
      time: fields.time.current?.validity.badInput,
    });
    if (found.date || found.time) {
      refuse(found);
      return;
    }
    send.mutate(undefined, {
      onError: (failure) => {
        const range = refusedRange(failure, playDeadline);
        if (range) {
          send.reset();
          refuse(range);
        } else store.reread();
      },
    });
  };

  const change = (field: ProposalField, value: string) => {
    setInputs((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
    if (send.isError) send.reset();
  };

  const consequenceId = `${idPrefix}-consequence`;
  return (
    <form noValidate aria-labelledby={`${idPrefix}-title`} className={PANEL} onSubmit={submit}>
      <h4 id={`${idPrefix}-title`} className="text-label text-ink">
        {copy.title}
      </h4>
      <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
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
          id={`${idPrefix}-time`}
          ref={fields.time}
          type="time"
          label={copy.time}
          value={inputs.time}
          error={errors.time}
          onChange={(event) => change("time", event.target.value)}
        />
      </div>
      <p id={consequenceId} className="text-body-phone text-ink-secondary">
        {replaces ? `${copy.consequence} ${copy.replaces}` : copy.consequence}
      </p>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Button type="submit" variant="primary" unavailable={send.isPending} aria-describedby={consequenceId}>
          {send.isPending ? copy.sending : copy.send}
        </Button>
        <button
          type="button"
          className={LINK_BUTTON}
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
