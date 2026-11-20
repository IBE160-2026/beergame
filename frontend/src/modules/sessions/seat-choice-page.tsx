"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";
import { cn } from "@/lib/utils";
import type { SessionUser } from "@/modules/identity/api";
import { GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { NotFoundPage } from "@/modules/identity/not-found-page";
import { PageLink, PageShell } from "@/modules/identity/page-shell";

import { type SeatChoice, type SeatChoiceGame, seatChoiceKey, takeSeat, useSeatChoice } from "./api";
import { canTake, freeCount, ownLine, seatText, takeLabel, whenLine } from "./seat-choice";
import { roleName } from "./sessions";

const copy = nb.sessions.seatChoice;

/**
 * «Velg spill og sete» (Story 5.17, FR-21, UX-DR62): a Student of a Class session with Student
 * choice sees its Klassespill, each with its four Seats in words («Grossist, ledig» or the holder's
 * name), Fabrikk first. Pressing a free Seat selects it and shows the primary button «Ta setet
 * Grossist i Spill 17» under its game; taking it holds the Seat, or moves the Student there from
 * the Seat they hold. When another Student took it first (409 `seat_taken`) the list is fetched
 * again and focus moves to «Setet ble tatt av en annen. Velg et annet.» above it, read once. Once
 * the session is locked the list is read-only and says the Seat the Student has, drawn or chosen.
 * The list is fetched when the screen opens and after each own action; refetching on `user:<id>`
 * comes with Story 6.4. While `FEATURE_STUDENT_CHOICE` is off the api answers not found.
 */
export function SeatChoicePage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="home">{(user, updatedAt) => <SeatChoiceView sessionId={sessionId} user={user} updatedAt={updatedAt} />}</GuardedPage>
  );
}

function SeatChoiceView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useSeatChoice(sessionId);
  const { phase, retry } = usePageState(found, seatChoiceKey(sessionId));
  if (found.error instanceof ApiRequestError && found.error.code === "not_found") return <NotFoundPage />;
  const choice = found.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={choice ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {/* The way back is «Til Hjem», as on every Student page; the breadcrumb is the staff's. */}
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      {choice ? <SeatChoiceBody sessionId={sessionId} choice={choice} /> : null}
    </PageShell>
  );
}

type Picked = { game: number; role: SeatChoiceGame["seats"][number]["role"] };

function SeatChoiceBody({ sessionId, choice }: { sessionId: string; choice: SeatChoice }) {
  const queryClient = useQueryClient();
  const [picked, setPicked] = useState<Picked | null>(null);
  const [conflict, setConflict] = useState(false);
  const [focusConflict, setFocusConflict] = useState(false);
  const [focusOwn, setFocusOwn] = useState(false);
  const conflictRef = useRef<HTMLParagraphElement>(null);
  const ownRef = useRef<HTMLParagraphElement>(null);
  // A picked Seat someone took meanwhile is no longer offered.
  const pickedSeat = picked
    ? choice.games.find((g) => g.number === picked.game)?.seats.find((s) => s.role === picked.role)
    : undefined;
  const shownPick = pickedSeat && canTake(choice, pickedSeat) ? picked : null;
  const take = useAction({
    mutationFn: async (at: Picked) => {
      try {
        return await takeSeat(sessionId, at.game, at.role);
      } catch (error) {
        if (error instanceof ApiRequestError && error.code === "seat_taken") {
          setPicked(null);
          setConflict(true);
          await queryClient.invalidateQueries({ queryKey: seatChoiceKey(sessionId), exact: true });
          setFocusConflict(true);
        } else if (
          error instanceof ApiRequestError &&
          (error.code === "session_locked" || error.code === "invalid_seat")
        ) {
          // The list on screen is out of date: the session has started, or the game is gone.
          await queryClient.invalidateQueries({ queryKey: seatChoiceKey(sessionId), exact: true });
        }
        throw error;
      }
    },
    messages: { session_locked: copy.closed, invalid_seat: copy.invalid, seat_taken: "" },
    fallback: copy.failed,
    onSuccess: (next) => {
      queryClient.setQueryData(seatChoiceKey(sessionId), next);
      setPicked(null);
      setConflict(false);
      // «Ditt sete: …» takes focus and is read once; it is the result.
      setFocusOwn(true);
    },
  });
  // The conflict line takes focus once the refreshed list is on screen, and is read once.
  useEffect(() => {
    if (!focusConflict) return;
    conflictRef.current?.focus();
    setFocusConflict(false);
  }, [focusConflict, choice]);
  useEffect(() => {
    if (!focusOwn) return;
    ownRef.current?.focus();
    setFocusOwn(false);
  }, [focusOwn, choice]);
  return (
    <div className="mt-2 flex flex-col gap-6">
      <div className="flex max-w-prose flex-col gap-1">
        <p className="text-body-phone text-ink lg:text-body">{copy.session(choice.class_name, choice.number)}</p>
        <p className="text-body-phone text-ink-secondary lg:text-body">{whenLine(choice)}</p>
        <p
          ref={ownRef}
          tabIndex={-1}
          className="mt-2 text-body-phone font-semibold text-ink focus:outline-none lg:text-body"
        >
          {ownLine(choice)}
        </p>
      </div>
      {conflict ? (
        <p
          ref={conflictRef}
          tabIndex={-1}
          className="max-w-prose border-l-2 border-ink pl-3 text-body-phone text-ink focus:outline-none lg:text-body"
        >
          {copy.conflict}
        </p>
      ) : null}
      <ol className="grid grid-cols-1 gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {choice.games.map((game) => (
          <li key={game.number} className="min-w-0">
            <GameSeats
              game={game}
              choice={choice}
              picked={shownPick}
              busy={take.isPending}
              onPick={(at) => {
                take.reset();
                setPicked(at);
              }}
              onTake={(at) => {
                if (take.isPending) return;
                setConflict(false);
                take.mutate(at);
              }}
              error={shownPick?.game === game.number ? take.errorMessage || undefined : undefined}
            />
          </li>
        ))}
      </ol>
    </div>
  );
}

/** One Klassespill: its number, how many Seats are free, and its four Seats as rows. A free Seat
 * is a button while the choice is open, marked «Velg» so it reads as one on a phone too; the
 * picked one is framed in `ink` and pressed. The Student's own Seat is the one row in bold. */
function GameSeats({
  game,
  choice,
  picked,
  busy,
  onPick,
  onTake,
  error,
}: {
  game: SeatChoiceGame;
  choice: SeatChoice;
  picked: Picked | null;
  busy: boolean;
  onPick: (at: Picked | null) => void;
  onTake: (at: Picked) => void;
  error: string | undefined;
}) {
  const ids = useId();
  const free = freeCount(game);
  const here = picked !== null && picked.game === game.number ? picked : null;
  return (
    <section aria-labelledby={`${ids}-title`} className="flex flex-col">
      <div className="flex items-baseline justify-between gap-3 border-b border-ink pb-1">
        <h2 id={`${ids}-title`} className="text-headline text-ink">
          {copy.game(game.number)}
        </h2>
        <span className="text-body-phone text-ink-secondary">{nb.sessions.seatChoice.freeCount(free)}</span>
      </div>
      <ul className="flex flex-col">
        {game.seats.map((seat) => {
          const text = seatText(seat);
          const isPicked = here !== null && here.role === seat.role;
          return (
            <li key={seat.role} className="border-b border-hairline">
              {canTake(choice, seat) ? (
                <button
                  type="button"
                  aria-pressed={isPicked}
                  className={cn(
                    "flex min-h-tap-target-min w-full cursor-pointer items-center justify-between gap-3 px-2 text-left text-body-phone text-ink hover:bg-hairline lg:text-body",
                    isPicked && "relative outline-2 -outline-offset-2 outline-ink outline-solid",
                  )}
                  onClick={() => onPick(isPicked ? null : { game: game.number, role: seat.role })}
                >
                  <span className="min-w-0">{text}</span>
                  {isPicked ? null : (
                    <span aria-hidden="true" className="shrink-0 text-label text-lager underline underline-offset-2">
                      {copy.pick}
                    </span>
                  )}
                </button>
              ) : (
                <p
                  className={cn(
                    "flex min-h-tap-target-min items-center px-2 text-body-phone break-words lg:text-body",
                    seat.mine ? "font-semibold text-ink" : "text-ink-secondary",
                  )}
                >
                  {text}
                </p>
              )}
            </li>
          );
        })}
      </ul>
      {here ? (
        <div className="mt-3 flex flex-col items-start gap-2">
          <Button variant="primary" unavailable={busy} onClick={() => onTake(here)}>
            {busy ? copy.taking : takeLabel(game.number, here.role)}
          </Button>
          {choice.my_seat ? (
            // Taking another Seat moves the Student: said before the press.
            <p className="text-body-phone text-ink-secondary">
              {copy.leaves(roleName(choice.my_seat.role), choice.my_seat.game_number)}
            </p>
          ) : null}
          <ActionError message={error} />
        </div>
      ) : null}
    </section>
  );
}
