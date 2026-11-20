"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type KeyboardEvent, type RefObject, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { ScrollRegion } from "@/components/scroll-region";
import { SegmentedChoice } from "@/components/segmented-choice";
import { ViewToggle } from "@/components/view-toggle";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import {
  changedReason,
  gameLabel,
  gameLine,
  gameState,
  holderName,
  invalidMoveReason,
  isChoosing,
  movedLine,
  nextGame,
  pickLabel,
  type SeatAt,
  seatMark,
  targetLabel,
  ticks,
  withoutSeatLine,
} from "./allocation";
import {
  type Allocation,
  type AllocationGame,
  type AllocationMethod,
  allocationKey,
  type ClassSession,
  confirmAllocation,
  lecturerHomeKey,
  moveInAllocation,
  openAllocation,
  redrawAllocation,
  useAllocation,
} from "./api";
import { osloDayAndTime } from "./dates";
import { roleName } from "./sessions";

const copy = nb.sessions.allocation;

/**
 * «Fordeling» on the Klasseøkt (Story 5.8, FR-20, UX-DR50): closed, the state line and a Lenke that
 * opens the Fordelingsforhåndsvisning in place, with focus moved to its heading. Opening draws the
 * draft when none is stored (a Lecturer before the Start date); the panel always shows the stored
 * draft. «Kjør fordeling på nytt» replaces it; nobody is told. «Bekreft fordeling» (Story 5.9) is
 * the page's primary button while the panel is open (`onConfirmShown` makes «Lagre Klasseøkt»
 * secondary meanwhile); it commits the draft shown and closes the panel to «Fordelingen er
 * bekreftet.», which takes focus. A confirmed allocation is not drawn again, and the open panel
 * says when it was confirmed (issue 107). Until the lock a Lecturer moves a Student to a free Seat
 * or swaps two from the selected game's Seats (Story 5.10), before and after the confirmation. An
 * Assistant lecturer, or anyone once the session is locked, reads the stored draft only. Once the
 * lock has opened the Class games (Story 5.12, `opened`), the api lists them as their Seats hold
 * them, with «KI-spiller» in every other Seat, and each game's line ends with its state. Once
 * locked, the block and the panel name the registered Students no Class game could seat (Story
 * 5.13); a late registrant is otherwise seated by the sweep within a minute.
 *
 * With `FEATURE_STUDENT_CHOICE` (Story 5.17) the block offers the allocation method as Valgknapper
 * until an allocation is confirmed; the choice (`method`) takes effect on «Lagre Klasseøkt». Once
 * Student choice is saved the block says the Students choose, and the panel shows the Class games
 * as their Seats hold them, read-only, with every empty Seat «Ledig».
 */
export function AllocationBlock({
  item,
  method = item.allocation_method,
  onMethodChange,
  onConfirmShown,
}: {
  item: ClassSession;
  /** The allocation method as chosen on the screen, saved with «Lagre Klasseøkt». */
  method?: AllocationMethod;
  onMethodChange?: (method: AllocationMethod) => void;
  onConfirmShown?: (shown: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const ids = useId();
  const found = useAllocation(item.id);
  const [open, setOpen] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const openerRef = useRef<HTMLButtonElement>(null);
  const stateRef = useRef<HTMLParagraphElement>(null);
  const allocation = found.data;
  const confirmed = allocation?.confirmed ?? false;
  const choosing = isChoosing(allocation);
  // Student choice chosen on the screen, not yet saved: nothing is drawn meanwhile.
  const choicePending = method === "student_choice" && item.allocation_method !== "student_choice";
  // Drawing and confirming end with the confirmation; moving and swapping last until the lock.
  // With Student choice the Students take the Seats themselves (Story 5.17).
  const studentChoice = item.allocation_method === "student_choice";
  const canDraw = item.can_manage && !item.locked && !confirmed && !studentChoice;
  const canMove = item.can_manage && !item.locked && !studentChoice;
  // Shown once the block is read, so a confirmed allocation never flashes the choice.
  const methodShown =
    allocation !== undefined &&
    item.student_choice_enabled &&
    item.can_manage &&
    !item.locked &&
    !studentChoice &&
    !confirmed;
  const confirmShown = open && allocation?.draft != null && canDraw;
  useEffect(() => {
    onConfirmShown?.(confirmShown);
    // Gone with the block, «Lagre Klasseøkt» is the primary button again.
    return () => onConfirmShown?.(false);
  }, [confirmShown, onConfirmShown]);
  // Why the panel closed by itself: every Student of the draft left the Klasse before a confirm.
  const [closedReason, setClosedReason] = useState<string | undefined>(undefined);
  const opening = useAction({
    mutationFn: () => openAllocation(item.id),
    messages: { session_locked: copy.locked },
    fallback: copy.failed,
    onSuccess: (result) => {
      queryClient.setQueryData(allocationKey(item.id), result);
      setOpen(true);
    },
  });
  // Where focus goes once the panel has closed: set before `setOpen(false)`, moved after the
  // commit that renders the target. A frame callback could run before that commit on a busy
  // machine, while the target is not on the page yet.
  const focusOnClose = useRef<"opener" | "state" | null>(null);
  useEffect(() => {
    if (open) {
      headingRef.current?.focus();
      return;
    }
    const target = focusOnClose.current;
    focusOnClose.current = null;
    if (target) (target === "state" ? stateRef : openerRef).current?.focus();
  }, [open]);

  const draft = allocation?.draft ?? null;
  const nobody = allocation !== undefined && allocation.registered_count === 0;
  // A draft stored before every Student left can still be seen, and cleared by a new draw.
  const openable =
    allocation !== undefined && !choicePending && (draft !== null || (!nobody && canDraw));
  // A redraw with nobody left removes the draft: the panel closes to the block.
  useEffect(() => {
    if (open && allocation !== undefined && draft === null) {
      focusOnClose.current = "opener";
      setOpen(false);
    }
  }, [open, allocation, draft]);

  if (open && allocation?.draft) {
    return (
      <section aria-labelledby={`${ids}-heading`} className="mt-10 min-w-0">
        <Preview
          item={item}
          allocation={allocation}
          headingId={`${ids}-heading`}
          headingRef={headingRef}
          canDraw={canDraw}
          canMove={canMove}
          onClose={() => {
            setClosedReason(undefined);
            focusOnClose.current = "opener";
            setOpen(false);
          }}
          onChanged={setClosedReason}
          onConfirmed={() => {
            setClosedReason(undefined);
            focusOnClose.current = "state";
            setOpen(false);
            void queryClient.invalidateQueries({ queryKey: lecturerHomeKey, exact: true });
          }}
        />
      </section>
    );
  }
  return (
    <section aria-labelledby={`${ids}-title`} className="mt-10 min-w-0">
      <h2 id={`${ids}-title`} className="text-headline text-ink">
        {copy.title}
      </h2>
      {allocation === undefined ? (
        found.isError ? (
          <p className="mt-2 text-body-phone text-ink-secondary">{copy.failed}</p>
        ) : null
      ) : (
        <p ref={stateRef} tabIndex={-1} className="mt-2 text-body-phone text-ink focus:outline-none lg:text-body">
          {allocation.opened
            ? copy.opened
            : choosing
              ? copy.choiceState
              : confirmed
                ? copy.confirmed
                : nobody && draft === null
                  ? copy.nobody
                  : copy.notConfirmed}
        </p>
      )}
      {methodShown && onMethodChange ? (
        <div className="mt-4">
          <SegmentedChoice<AllocationMethod>
            name="allocation-method"
            className="lg:[&_label]:flex-none"
            legend={copy.method}
            options={[
              { value: "random", label: copy.methodRandom },
              { value: "student_choice", label: copy.methodChoice },
            ]}
            value={method}
            onChange={onMethodChange}
            describedBy={`${ids}-method`}
          />
          <p id={`${ids}-method`} className="mt-2 max-w-prose text-body-phone text-ink-secondary">
            {method === "student_choice" ? copy.methodChoiceHelp : copy.methodRandomHelp}
          </p>
          {choicePending ? (
            <p className="mt-2 max-w-prose text-body-phone text-ink lg:text-body">{copy.methodChoicePending}</p>
          ) : null}
        </div>
      ) : null}
      {allocation && withoutSeatLine(allocation) ? (
        <p className="mt-2 max-w-prose text-body-phone text-ink lg:text-body">{withoutSeatLine(allocation)}</p>
      ) : null}
      {openable ? (
        <button
          ref={openerRef}
          type="button"
          className={LINK_BUTTON}
          aria-disabled={opening.isPending || undefined}
          onClick={() => {
            if (opening.isPending) return;
            setClosedReason(undefined);
            if (canDraw) opening.mutate();
            else setOpen(true);
          }}
        >
          {opening.isPending ? copy.opening : copy.open}
        </button>
      ) : null}
      <ActionError message={opening.errorMessage ?? closedReason} />
    </section>
  );
}

type View = "chart" | "list";

function Preview({
  item,
  allocation,
  headingId,
  headingRef,
  canDraw,
  canMove,
  onClose,
  onChanged,
  onConfirmed,
}: {
  item: ClassSession;
  allocation: Allocation;
  headingId: string;
  headingRef: RefObject<HTMLHeadingElement | null>;
  canDraw: boolean;
  canMove: boolean;
  onClose: () => void;
  onChanged: (reason: string | undefined) => void;
  onConfirmed: () => void;
}) {
  const queryClient = useQueryClient();
  const ids = useId();
  const draft = allocation.draft!;
  const games = draft.games;
  const [view, setView] = useState<View>("chart");
  const [selected, setSelected] = useState(1);
  const [result, setResult] = useState("");
  const shown = games.find((game) => game.number === selected) ?? games[0];
  const choosing = isChoosing(allocation);
  const students = games.reduce((sum, game) => sum + game.seats.filter((seat) => seat.user_id != null).length, 0);
  const redraw = useAction({
    mutationFn: () => redrawAllocation(item.id),
    messages: { session_locked: copy.locked, allocation_confirmed: copy.redrawConfirmed },
    fallback: copy.failed,
    onSuccess: (next) => {
      queryClient.setQueryData(allocationKey(item.id), next);
      setSelected(1);
      setResult(copy.redrawn);
    },
  });
  // «Bekreft fordeling» sends the draft on screen; a stale one answers 409 `allocation_changed`,
  // and the current draft is read again so the next press confirms what is then shown.
  const confirm = useAction({
    mutationFn: async () => {
      try {
        return await confirmAllocation(item.id, draft.id, draft.revision);
      } catch (error) {
        if (error instanceof ApiRequestError && error.code === "allocation_changed") {
          setSelected(1);
          // Said again by the block if the draft is gone and the panel closes.
          onChanged(changedReason(error.fields));
          await queryClient.invalidateQueries({ queryKey: allocationKey(item.id), exact: true });
        }
        throw error;
      }
    },
    messages: { session_locked: copy.confirmLocked },
    fallback: copy.confirmFailed,
    onSuccess: (next) => {
      queryClient.setQueryData(allocationKey(item.id), next);
      onConfirmed();
    },
  });
  const confirmError =
    confirm.error instanceof ApiRequestError && confirm.error.code === "allocation_changed"
      ? changedReason(confirm.error.fields)
      : confirm.errorMessage;
  // Moving and swapping (Story 5.10): pick a Student, choose any game in the chart, then press the
  // button on the Seat to move to. The request carries the revision on screen.
  const [picked, setPicked] = useState<Picked | null>(null);
  const pickedAt = seatAt(games, picked);
  const seatRefs = useRef(new Map<string, HTMLButtonElement>());
  const [focusSeat, setFocusSeat] = useState<string | null>(null);
  useEffect(() => {
    if (focusSeat === null) return;
    seatRefs.current.get(focusSeat)?.focus();
    setFocusSeat(null);
  }, [focusSeat, allocation]);
  const move = useAction({
    mutationFn: async ({ from, to }: { from: SeatAt; to: SeatAt }) => {
      try {
        return await moveInAllocation(item.id, draft.id, draft.revision, {
          from_game: from.game,
          from_role: from.seat.role,
          to_game: to.game,
          to_role: to.seat.role,
        });
      } catch (error) {
        if (error instanceof ApiRequestError && error.code === "allocation_changed") {
          setPicked(null);
          await queryClient.invalidateQueries({ queryKey: allocationKey(item.id), exact: true });
        }
        throw error;
      }
    },
    messages: {
      session_locked: copy.moveLocked,
      game_already_started: copy.moveStarted,
      allocation_changed: copy.changed,
    },
    fallback: copy.moveFailed,
    onSuccess: (next, { from, to }) => {
      queryClient.setQueryData(allocationKey(item.id), next);
      setPicked(null);
      setSelected(to.game);
      setResult(movedLine(from, to));
      setFocusSeat(seatKey(to.game, to.seat.role));
    },
  });
  const moveError =
    move.error instanceof ApiRequestError && move.error.code === "invalid_move"
      ? invalidMoveReason(move.error.fields)
      : move.errorMessage;
  const confirmedAt = allocation.confirmed && allocation.confirmed_at ? osloDayAndTime(allocation.confirmed_at) : null;
  const busy = redraw.isPending || confirm.isPending || move.isPending;
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 id={headingId} ref={headingRef} tabIndex={-1} className="text-headline text-ink focus:outline-none">
          {copy.heading(games.length)}
        </h2>
        {allocation.opened ? (
          <p className="mt-2 max-w-prose text-body-phone font-semibold text-ink lg:text-body">{copy.opened}</p>
        ) : null}
        {choosing ? (
          // Student choice (Story 5.17): its empty draft is confirmed by the save, so the
          // Lecturer confirmed nothing; the panel says what the block says.
          <p className="mt-2 max-w-prose text-body-phone font-semibold text-ink lg:text-body">{copy.choiceState}</p>
        ) : confirmedAt ? (
          <p
            className={cn(
              "max-w-prose text-body-phone lg:text-body",
              allocation.opened ? "text-ink-secondary" : "mt-2 font-semibold text-ink",
            )}
          >
            {copy.confirmedOn(confirmedAt.day, confirmedAt.time)}
          </p>
        ) : null}
        <p className="mt-2 max-w-prose text-body-phone text-ink-secondary lg:text-body">
          {allocation.opened
            ? copy.openedLead(students, games.length)
            : choosing
              ? copy.choiceLead(students)
              : copy.lead(students)}
        </p>
        <p className="max-w-prose text-body-phone text-ink-secondary lg:text-body">
          {allocation.opened ? copy.openedSeats : choosing ? copy.choiceEmptySeats : copy.emptySeats}
        </p>
        {withoutSeatLine(allocation) ? (
          <p className="mt-2 max-w-prose text-body-phone text-ink lg:text-body">{withoutSeatLine(allocation)}</p>
        ) : allocation.missing_count > 0 ? (
          <p className="mt-2 max-w-prose text-body-phone text-ink">
            {choosing ? copy.choiceMissing(allocation.missing_count) : copy.missing(allocation.missing_count)}
            {canDraw ? ` ${copy.missingRedraw}` : null}
          </p>
        ) : null}
      </div>
      <ViewToggle<View>
        name={`${ids}-view`}
        legend={copy.view}
        options={[
          { value: "chart", label: copy.chart },
          { value: "list", label: copy.list },
        ]}
        value={view}
        onChange={setView}
        className="lg:[&_label]:flex-none"
      />
      {view === "chart" ? (
        <>
          <p id={`${ids}-chart`} className="sr-only">
            {copy.chartLabel}
          </p>
          <ScrollRegion labelledBy={`${ids}-chart`}>
            <AllocationChart games={games} selected={shown.number} onSelect={setSelected} choosing={choosing} />
          </ScrollRegion>
          {canMove ? (
            <SeatList
              game={shown}
              picked={pickedAt}
              busy={busy}
              refs={seatRefs.current}
              error={moveError}
              onPick={(at) => {
                move.reset();
                setResult("");
                setPicked(at === null ? null : { game: at.game, role: at.seat.role, userId: at.seat.user_id! });
              }}
              onTarget={(to) => {
                if (busy || pickedAt === null) return;
                confirm.reset();
                redraw.reset();
                move.mutate({ from: pickedAt, to });
              }}
            />
          ) : (
            <p className="text-body-phone text-ink lg:text-body">
              <span className="mr-3 font-semibold">{copy.game(shown.number)}</span>
              {gameLine(shown, choosing)}
              <GameState game={shown} />
            </p>
          )}
        </>
      ) : (
        <ol aria-label={copy.heading(games.length)} className="flex flex-col gap-1">
          {games.map((game) => (
            <li key={game.number} className="text-body-phone text-ink lg:text-body">
              <span className="mr-3 font-semibold">{copy.game(game.number)}</span>
              {gameLine(game, choosing)}
              <GameState game={game} />
            </li>
          ))}
        </ol>
      )}
      <div className="flex flex-col items-start gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:gap-x-6">
        {canDraw ? (
          <>
            <Button
              variant="secondary"
              unavailable={busy}
              onClick={() => {
                if (busy) return;
                // Cleared first, so a second redraw is announced again.
                setResult("");
                setPicked(null);
                move.reset();
                confirm.reset();
                redraw.mutate();
              }}
            >
              {redraw.isPending ? copy.redrawing : copy.redraw}
            </Button>
            <Button
              variant="primary"
              unavailable={busy}
              aria-describedby={`${ids}-notice`}
              onClick={() => {
                if (busy) return;
                setResult("");
                setPicked(null);
                redraw.reset();
                move.reset();
                confirm.mutate();
              }}
            >
              {confirm.isPending ? copy.confirming : copy.confirm}
            </Button>
            <p id={`${ids}-notice`} className="text-body-phone text-ink-secondary">
              {copy.noticeLine}
            </p>
          </>
        ) : canMove && allocation.confirmed ? (
          <p className="text-body-phone text-ink-secondary">{copy.movedNotice}</p>
        ) : null}
        <button type="button" className={LINK_BUTTON} onClick={onClose}>
          {copy.close}
        </button>
      </div>
      <ActionError message={redraw.errorMessage ?? confirmError} />
      <p role="status" className="text-body-phone text-ink">
        {result}
      </p>
    </div>
  );
}

/** An opened Class game's state, set apart from the last Seat it follows (Story 5.12). */
function GameState({ game }: { game: AllocationGame }) {
  const state = gameState(game);
  return state ? <span className="ml-3 whitespace-nowrap text-ink-secondary">{state}</span> : null;
}

const seatKey = (game: number, role: string) => `${game}:${role}`;

/** A picked Student: the Seat and who held it when picked. */
type Picked = { game: number; role: string; userId: string };

/** The picked Seat as the draft now holds it; null once another Student holds it, or none (a
 * draft read again after an edit elsewhere), so a move never goes out for someone not picked. */
function seatAt(games: AllocationGame[], picked: Picked | null): SeatAt | null {
  if (picked === null) return null;
  const seat = games.find((game) => game.number === picked.game)?.seats.find((s) => s.role === picked.role);
  return seat && seat.user_id === picked.userId ? { game: picked.game, seat } : null;
}

/**
 * The selected game's Seats, Fabrikk first, where Students are moved and swapped (Story 5.10,
 * UX-DR9, UX-DR50): no drag. Each Student's row has «Flytt eller bytt»; once one is picked, every
 * other Seat of whichever game is selected offers «Bytt» (a Student there) or «Flytt» (a free
 * Seat). The short visible text starts the accessible name, which names the Student, the Role and
 * the Klassespill in full.
 */
function SeatList({
  game,
  picked,
  busy,
  refs,
  error,
  onPick,
  onTarget,
}: {
  game: AllocationGame;
  picked: SeatAt | null;
  busy: boolean;
  refs: Map<string, HTMLButtonElement>;
  /** A refused move, said beside the Seat buttons that sent it (EXPERIENCE.md → Action error). */
  error: string | undefined;
  onPick: (at: SeatAt | null) => void;
  onTarget: (at: SeatAt) => void;
}) {
  const ids = useId();
  return (
    <section aria-labelledby={`${ids}-seats`} className="flex flex-col">
      <h3 id={`${ids}-seats`} className="text-label text-ink">
        {copy.seatsHeading(game.number)}
      </h3>
      {/* Who is picked stays said while another game is chosen in the chart. */}
      <p role="status" className="mt-1 max-w-prose text-body-phone text-ink lg:text-body">
        {picked ? copy.picked(holderName(picked.seat), roleName(picked.seat.role), picked.game) : ""}
      </p>
      <ul className="mt-2 flex max-w-xl flex-col border-t border-hairline">
        {game.seats.map((seat) => {
          const at: SeatAt = { game: game.number, seat };
          const key = seatKey(game.number, seat.role);
          const isPicked = picked !== null && picked.game === game.number && picked.seat.role === seat.role;
          const setRef = (node: HTMLButtonElement | null) => {
            if (node) refs.set(key, node);
            else refs.delete(key);
          };
          let action = null;
          if (isPicked) {
            action = (
              <Button ref={setRef} unavailable={busy} aria-pressed onClick={() => onPick(null)}>
                {copy.cancelPick}
              </Button>
            );
          } else if (picked !== null) {
            action = (
              <Button ref={setRef} unavailable={busy} aria-label={targetLabel(picked, at)} onClick={() => onTarget(at)}>
                {seat.user_id != null ? copy.swapShort : copy.moveShort}
              </Button>
            );
          } else if (seat.user_id != null) {
            action = (
              <Button ref={setRef} unavailable={busy} aria-label={pickLabel(at)} onClick={() => onPick(at)}>
                {copy.pickShort}
              </Button>
            );
          }
          return (
            <li
              key={key}
              data-seat={seat.role}
              // Phone: Role and name on one line, the button under them at full width. Wider: one
              // line, the buttons in one right-hand column of one width.
              className="grid min-h-tap-target-min grid-cols-[6rem_minmax(0,1fr)] items-center gap-x-4 gap-y-2 border-b border-hairline py-2 sm:grid-cols-[7rem_minmax(0,1fr)_10rem] sm:py-1"
            >
              <span className="text-body-phone text-ink-secondary lg:text-body">{roleName(seat.role)}</span>
              <span
                className={cn(
                  "min-w-0 break-words text-body-phone lg:text-body",
                  seat.user_id != null ? "text-ink" : "text-ink-muted",
                  isPicked && "font-semibold",
                )}
              >
                {holderName(seat)}
              </span>
              {action ? <div className="col-span-2 flex sm:col-span-1 [&>button]:w-full">{action}</div> : null}
            </li>
          );
        })}
      </ul>
      <ActionError message={error} className="mt-2 max-w-prose" />
    </section>
  );
}

// Drawn at its natural width, one SVG unit to one CSS pixel, so the 13 px labels keep DESIGN.md's
// floor; a wide allocation scrolls in its own region (UX-DR75).
const LABEL = 92;
const FONT = 13;
const ROW = 30;
const ROW_GAP = 6;
const TOP = 6;
const TICKS = 22;
const ROOM = 460;

/** Whether the element got focus the way `:focus-visible` shows a ring (the keyboard). */
function focusVisible(element: Element): boolean {
  try {
    return element.matches(":focus-visible");
  } catch {
    return true;
  }
}

/** The column pitch: wide while there are few games, down to 10 px as in mockup 03. */
function pitchFor(count: number): number {
  return Math.max(10, Math.min(48, Math.floor(ROOM / Math.max(1, count))));
}

/**
 * The Fordelingsforhåndsvisning (UX-DR50, UX-DR73): one column per Class game by four Role rows,
 * Fabrikk at the top, a filled `bar-base` cell for a Student and an outlined one for an empty Seat
 * (KI-spiller). The selected column is framed in `ink`. A diagram of this slice in plain SVG, not
 * an AD-18 chart. The columns are one tab stop: ←/→, Home and End move the selection, a click
 * selects. The selected game's line under it and «Vis som liste» say the same in text.
 */
function AllocationChart({
  games,
  selected,
  onSelect,
  choosing = false,
}: {
  games: AllocationGame[];
  selected: number;
  onSelect: (number: number) => void;
  /** Students choose (Story 5.17): an empty Seat is named «Ledig». */
  choosing?: boolean;
}) {
  const refs = useRef(new Map<number, SVGGElement>());
  const [focused, setFocused] = useState(false);
  const pitch = pitchFor(games.length);
  const cell = Math.max(7, Math.round(pitch * 0.78));
  const roles = games[0]?.seats.map((seat) => seat.role) ?? [];
  const height = TOP + roles.length * (ROW + ROW_GAP) + TICKS;
  const width = LABEL + games.length * pitch + 16;
  // Whole pixels, so the 1 px outlines and the frame below fall on the pixel grid and stay `ink`.
  const x = (index: number) => LABEL + index * pitch + Math.floor((pitch - cell) / 2);
  const y = (row: number) => TOP + row * (ROW + ROW_GAP);
  const move = (event: KeyboardEvent<SVGGElement>) => {
    const next = nextGame(event.key, selected, games.length);
    if (next !== null) {
      event.preventDefault();
      onSelect(next);
      refs.current.get(next)?.focus();
    } else if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
    }
  };
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block" focusable="false">
      {roles.map((role, row) => (
        <text
          key={role}
          x={0}
          y={y(row) + ROW / 2 + FONT / 2 - 2}
          fontSize={FONT}
          fill="var(--color-ink)"
          aria-hidden="true"
        >
          {roleName(role)}
        </text>
      ))}
      {games.map((game, index) => {
        const isSelected = game.number === selected;
        return (
          <g
            key={game.number}
            ref={(node) => {
              if (node) refs.current.set(game.number, node);
              else refs.current.delete(game.number);
            }}
            role="button"
            tabIndex={isSelected ? 0 : -1}
            aria-pressed={isSelected}
            aria-label={gameLabel(game, choosing)}
            className="cursor-pointer outline-none"
            onClick={() => onSelect(game.number)}
            onKeyDown={move}
            // The thick ring only for the keyboard: a click selects with the 1 px frame.
            onFocus={(event) => setFocused(focusVisible(event.currentTarget))}
            onBlur={() => setFocused(false)}
          >
            {/* The whole column takes the click, gaps included. */}
            <rect x={LABEL + index * pitch} y={0} width={pitch} height={y(roles.length)} fill="transparent" />
            {game.seats.map((seat, row) => {
              const mark = seatMark(seat);
              return mark === "student" ? (
                <rect
                  key={seat.role}
                  data-seat={mark}
                  x={x(index)}
                  y={y(row)}
                  width={cell}
                  height={ROW}
                  fill="var(--color-bar-base)"
                />
              ) : (
                // An empty Seat is outlined; a removed Student's is outlined in `ink`, dashed, so it
                // reads apart from both (issue 106). The game line names it in words.
                <rect
                  key={seat.role}
                  data-seat={mark}
                  x={x(index) + 0.5}
                  y={y(row) + 0.5}
                  width={cell - 1}
                  height={ROW - 1}
                  fill="var(--color-paper)"
                  stroke={mark === "removed" ? "var(--color-ink)" : "var(--color-ink-muted)"}
                  strokeWidth={1}
                  strokeDasharray={mark === "removed" ? "3 2" : undefined}
                />
              );
            })}
          </g>
        );
      })}
      {/* The frame is drawn over every column, so the next column's cells never cover its edge. */}
      {games.map((game, index) =>
        game.number === selected ? (
          <rect
            key="selected"
            // Odd stroke widths centred on a half pixel, so the line is crisp, not a grey blur.
            x={x(index) - 1.5}
            y={y(0) - 2.5}
            width={cell + 3}
            height={y(roles.length) - ROW_GAP - y(0) + 5}
            fill="none"
            stroke="var(--color-ink)"
            // 1 px as DESIGN.md frames a selection; 3 px, the focus ring, while the keyboard is on it.
            strokeWidth={focused ? 3 : 1}
            data-frame={focused ? "focus" : "selected"}
            pointerEvents="none"
          />
        ) : null,
      )}
      {ticks(games.length, selected, Math.ceil(28 / pitch)).map((number) => (
        <text
          key={number}
          x={LABEL + (number - 1) * pitch + pitch / 2}
          y={height - 4}
          fontSize={FONT}
          textAnchor="middle"
          fontWeight={number === selected ? 600 : 400}
          fill={number === selected ? "var(--color-ink)" : "var(--color-ink-muted)"}
          aria-hidden="true"
        >
          {number}
        </text>
      ))}
    </svg>
  );
}
