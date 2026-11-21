"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError, isSessionExpired } from "@/lib/api/client";
import { errorCode } from "@/lib/api/mutation";
import { clearDraft, clearDrafts, loadDraft, saveDraft } from "@/lib/drafts";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { orderPreview } from "@/lib/preview";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH, rulesPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, placeOrder, type PlayEnvelope, playKey, useMyGame, usePlay, viewWeek } from "./api";
import { ChainBandView } from "./chain-band-view";
import { GameAction } from "./game-action";
import { OrderField } from "./order-field";
import { lastOrder, parseOrder } from "./order-input";
import { gameTitle } from "./home";
import { useServerNow, waitedFor } from "./seat-status";
import { GameSeatStatus } from "./seat-status-view";
import { weekSummary } from "./week-summary";
import { WeekSummaryView } from "./week-summary-view";
import { ROWS } from "./week-table";
import { WeekTable } from "./week-table-view";

const copy = nb.games.play;
const LINE = "text-body-phone lg:text-body";

/**
 * The play route (Stories 6.5 and 6.6, FR-22, FR-23, FR-73, mockup `05-spill.png`): while the game
 * runs, the Topplinje («Uke 11» over «Grossist, Spill 17», «Totalkostnad» over the amount at the
 * right), the week table from the play envelope (`/api/me/games/{id}/play`), a Lenke to «Regler
 * før første ordre» and «Setene», each Seat's Role and who holds it in words («KI-spiller» for
 * every AI player). From 1024 px the table stands left and the rest in a right column. Never the
 * number of Weeks. Over the table the Seat's own link stands as the Kjedebånd (Story 6.9). In a
 * Veiledet uke the Ordrefelt shows the fixed Order read-only, and the page tells the api once that
 * the Student has the Week on screen, which counts as their Order there (Story 6.10). After them
 * the Student types the Order, previewed in the table and the Kjedebånd (Story 6.11), kept as a
 * draft in this browser until it is sent, and sends it with «Bekreft ordre på 24» (Story 6.12).
 * Under the Ordrefelt the Setestatus shows who has ordered this Uke and whom the game waits for, for
 * how long (Story 6.14); the envelope is read again at its `next_change_at`. When the Uke moves on
 * (Story 6.15) the Uke-overgang above the Ordrefelt says what the Uke just run did, until the own
 * Order; on an open page it is announced and the now-line moves one column. A game that has not started, or that this Student may
 * not play before the briefing and Starting task, shows its next action (briefing, «Start spillet» or the not-ready line); a finished one says so. The
 * page follows the game's `game:` events (`topics.ts`). Another Student's game shows the
 * permission-denied page.
 */
export function PlayPage({ gameId }: { gameId: string }) {
  return (
    <GuardedPage page="home">{(user, updatedAt) => <PlayView gameId={gameId} user={user} updatedAt={updatedAt} />}</GuardedPage>
  );
}

function PlayView({ gameId, user, updatedAt }: { gameId: string; user: SessionUser; updatedAt: number }) {
  const found = useMyGame(gameId);
  const { phase, retry } = usePageState(found, myGameKey(gameId));
  const game = found.data;
  // The pre-play gate holds here too: a game another Student started shows «Les reglene» until
  // this Student has done the Starting task.
  const running = game?.status === "running" && game.week != null && !game.briefing_first;
  // The envelope is asked for only while the game runs; its wait follows the game's.
  const envelope = usePlay(gameId, running);
  const play = usePageState(envelope, playKey(gameId));
  // A game that stopped running between the two reads: read the game again, which then shows
  // where it stands (finished, or its next action).
  const stopped = envelope.error instanceof ApiRequestError && envelope.error.code === "game_not_running";
  const refetchGame = found.refetch;
  useEffect(() => {
    if (stopped) void refetchGame();
  }, [stopped, refetchGame]);
  const denied = [found.error, envelope.error].some((e) => e instanceof ApiRequestError && e.code === "forbidden");
  if (denied) return <AccessDenied user={user} updatedAt={updatedAt} />;
  const shown = running && envelope.data ? envelope.data : null;
  const pagePhase = !game
    ? phase === "ready"
      ? "loading"
      : phase
    : running && !shown
      ? play.phase === "ready"
        ? "loading"
        : play.phase
      : "ready";
  return (
    <PageShell
      user={user}
      title={game ? (running ? copy.week(shown?.seat_state.week ?? game.week!) : gameTitle(game)) : undefined}
      header={game && shown ? <Topplinje game={game} envelope={shown} /> : undefined}
      updatedAt={updatedAt}
      phase={pagePhase}
      onRetry={() => {
        retry();
        if (running) play.retry();
      }}
      skeleton={SKELETON}
    >
      {game ? shown ? <Running game={game} envelope={shown} userId={user.id} /> : running ? null : <NotRunning game={game} /> : null}
    </PageShell>
  );
}

/** The Skjelett in the week table's real rows («Uke» and the phone's rows) and 12 columns. */
const SKELETON = { rows: 1 + ROWS.filter((row) => !row.laptopOnly).length, columns: 12 };

/** The Topplinje (DESIGN.md → Topplinje, UX-DR13): «Uke 11» over «Grossist, Spill 17», and
 * «Totalkostnad» over the amount at the right. Never the number of Uker (FR-14). */
function Topplinje({ game, envelope }: { game: MyGame; envelope: PlayEnvelope }) {
  const state = envelope.seat_state;
  return (
    <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
      <div className="min-w-0">
        {/* Takes focus when the Student's own Order completed the Uke and the next one shows. */}
        <h1 id={WEEK_HEADING} tabIndex={-1} className="text-title-phone text-ink outline-none lg:text-title-page">
          {copy.week(state.week)}
        </h1>
        <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleGame(roleName(game.role), game.number)}</p>
      </div>
      <p className="text-right">
        <span className="block text-caption text-ink-secondary">{nb.terms.totalCost}</span>
        <span className="block text-figure-total text-ink tabular-nums lining-nums">
          {formatNumber(state.total_cost, { kroner: true })}
        </span>
      </p>
    </div>
  );
}

const WEEK_HEADING = "play-week";

/** The draft field of the typed Order of `gameId` in Uke `week` (`lib/drafts.ts`). */
const orderDraftPrefix = (gameId: string) => `order:${gameId}:`;
const orderDraftField = (gameId: string, week: number) => `${orderDraftPrefix(gameId)}${week}`;

function Running({ game, envelope, userId }: { game: MyGame; envelope: PlayEnvelope; userId: string }) {
  useGuidedView(game.id, envelope);
  useRefetchAt(game.id, envelope);
  const now = useServerNow(envelope.server_now);
  const seats = envelope.table_status.seats;
  const state = envelope.seat_state;
  const turn = envelope.turn;
  const field = orderDraftField(game.id, state.week);
  // The typed Order belongs to its game and Uke: a new Uke starts empty, unless this browser
  // kept a draft of that very Uke for this User (a reload, a page left, an ended session).
  const [typed, setTyped] = useState<{ game: string; week: number; text: string } | null>(null);
  const text = typed?.game === game.id && typed.week === state.week ? typed.text : (loadDraft(userId, field) ?? "");
  const editable = !turn.guided && turn.order == null;
  // Drafts of the game's other Uker are of no use any more; nor is this Uke's once it is ordered.
  useEffect(() => {
    clearDrafts(userId, orderDraftPrefix(game.id), editable ? field : undefined);
  }, [userId, game.id, field, editable]);
  const send = useSendOrder(game.id, state.week, userId, field);
  const parsed = parseOrder(text, state.max_order);
  // The live preview (Story 6.11, AD-10): a valid value on an editable field, and the sent Order
  // after it, which the table and the Kjedebånd keep showing (Story 6.12, `06` C).
  const placed = !turn.guided && turn.order != null ? turn.order : null;
  const preview =
    placed !== null
      ? { ...orderPreview(state.preview, placed), confirmed: true }
      : editable && parsed.kind === "valid"
        ? orderPreview(state.preview, parsed.value)
        : null;
  const movedFrom = useMovedFrom(state.week);
  const [moving, setMoving] = useState(false);
  const [skip, setSkip] = useState(0);
  const summary = weekSummary(state, turn);
  const dropped = useDroppedDraft(state, text, editable, send.outcome);
  return (
    <div className="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12">
      <div className="min-w-0">
        {/* Reading and focus order: Topplinje, Kjedebånd, Graf over tabell, the rest (FR-73). */}
        <ChainBandView state={state} seatRoles={game.seats.map((seat) => seat.role)} typed={preview?.order} />
        {/* A placed Order (a Veiledet uke's fixed Order) stands in Din ordre at nå; a typed one
            there and at its arrival Uke. */}
        <WeekTable
          state={state}
          nowOrder={turn.guided ? (turn.order ?? undefined) : undefined}
          typed={preview ?? undefined}
          movedFrom={movedFrom}
          skipMove={skip}
          onMoving={setMoving}
        />
      </div>
      <div>
        {/* The Uke-overgang over the Ordrefelt, which is usable at once (Story 6.15). */}
        {summary ? <WeekSummaryView summary={summary} moving={moving} onSkip={() => setSkip((n) => n + 1)} /> : null}
        {/* Read when the Uke moved on while the page was open, not on load. */}
        <p aria-live="polite" className="sr-only" data-week-announce="">
          {summary && movedFrom !== undefined ? summary.spoken : ""}
        </p>
        <div aria-live="polite" data-draft-dropped="">
          {dropped.line ? <p className={`${LINE} mt-8 max-w-md font-bold text-ink lg:mt-0 lg:mb-4`}>{dropped.line}</p> : null}
        </div>
        {/* The Ordrefelt follows the table on phone and tops the right column on laptop. */}
        <OrderField
          week={state.week}
          turn={turn}
          max={state.max_order}
          lastOrder={lastOrder(state.history)}
          text={text}
          onText={(next) => {
            setTyped({ game: game.id, week: state.week, text: next });
            saveDraft(userId, field, next);
            send.clear(); // a new value is a new Order: the last send's words no longer apply
            dropped.clear();
          }}
          preview={editable ? preview : null}
          sending={send.sending === state.week}
          onConfirm={(value) => {
            dropped.clear();
            send.confirm(value);
          }}
          waitingFor={waitedFor(seats, now, true)}
          {...outcomeProps(send.outcome, state.week)}
        />
        {/* Through the whole Uke, before and after the own Order, right under the Ordrefelt. */}
        <GameSeatStatus seats={seats} now={now} titleId={`seats-${game.id}`} className="max-w-md" />
        <PageLink href={rulesPath(game.id)}>{nb.games.briefing.title}</PageLink>
        <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      </div>
    </div>
  );
}

/**
 * The Uke that was nå before this one, when the page saw the Uke move on (Story 6.15): the
 * now-line moves from it and the Uke-overgang is announced. Undefined on the Uke the page opened
 * at (a load, a reload, another device), so nothing moves or is read then.
 */
function useMovedFrom(week: number): number | undefined {
  const [seen, setSeen] = useState<{ week: number; from?: number }>({ week });
  if (seen.week !== week) {
    // One Uke on: a jump of several (a reconnect after missed events) moves and reads nothing.
    const next = { week, from: week === seen.week + 1 ? seen.week : undefined };
    setSeen(next);
    return next.from;
  }
  return seen.from;
}

/**
 * A typed Order that was never sent when its Uke closed on an open page (Story 6.15, NFR-5): the
 * Seat's Order came from elsewhere (another device), so the draft is dropped (`clearDrafts`) and a
 * line says so, until the Student types or sends again, or the next Uke comes. Not when the Uke's stored Order is the
 * typed value, nor when a send of it already said what happened (Story 6.13).
 */
function useDroppedDraft(state: PlayEnvelope["seat_state"], text: string, editable: boolean, outcome: SendOutcome | null) {
  const previous = useRef<{ week: number; text: string; editable: boolean } | null>(null);
  const [dropped, setDropped] = useState<{ week: number; value: string } | null>(null);
  useEffect(() => {
    const was = previous.current;
    previous.current = { week: state.week, text, editable };
    // A line about an earlier Uke goes when the Uke moves on again.
    if (was && state.week !== was.week) setDropped(null);
    if (!was || state.week <= was.week || !was.editable || outcome?.week === was.week) return;
    const typed = parseOrder(was.text, state.max_order);
    if (was.text.trim() === "") return;
    const stored = state.history.find((row) => row.week === was.week)?.order;
    if (typed.kind === "valid" && stored === typed.value) return;
    setDropped({ week: was.week, value: was.text.trim() });
  }, [state, text, editable, outcome]);
  return {
    line: dropped ? copy.summary.draftDropped(dropped.week, dropped.value) : null,
    clear: () => setDropped(null),
  };
}

/** How long a sent Order may go unanswered before the app asks the server whether it arrived
 * (Story 6.13, EXPERIENCE.md → Timed out: a placeholder of 10 s). The check is bounded alike. */
export const ORDER_SUBMIT_TIMEOUT_MS = 10_000;

/** What the last send left to say, for the Uke it was sent in (Story 6.13). */
type SendOutcome = { week: number; value: number; kind: "checking" | "failed" | "weekGone" | "seatGone" };

/** Rejects with `network_error` when `promise` has not settled after `ms`. */
function within<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const late = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new ApiRequestError(0, "network_error")), ms);
  });
  return Promise.race([promise, late]).finally(() => clearTimeout(timer));
}

/**
 * «Bekreft ordre på 24» (Stories 6.12 and 6.13, AD-2, UX-DR60): sends the Order once (a press while
 * it is on its way does nothing), with no `version`, as a mutation, so an ended session goes to
 * «Logg inn» (`providers.tsx`) with the draft kept. A send unanswered after
 * `ORDER_SUBMIT_TIMEOUT_MS` is aborted and the screen says it is checking. Whatever went wrong
 * (but an ended session), the play envelope is read again before anything is said, each read
 * bounded by the same timeout: an Order that is stored (`order_exists` included, or an Uke that
 * moved on with this value in its history) is Confirmed like a success; otherwise the screen says
 * why it was not sent, and a retry is safe since the api never places a second Order. After a
 * success the draft is dropped and focus moves to «Ordren på 24 er sendt.»,
 * or to the new Uke's heading when the Uke moved on. Live updates never move focus: only this send
 * does.
 */
function useSendOrder(gameId: string, week: number, userId: string, field: string) {
  const queryClient = useQueryClient();
  const inFlight = useRef(false);
  // The Uke whose Order is on its way: a new Uke shown meanwhile is not Submitting.
  const [sending, setSending] = useState<number | null>(null);
  const [outcome, setOutcome] = useState<SendOutcome | null>(null);
  const [sent, setSent] = useState<number | null>(null);
  const mutation = useMutation({
    mutationFn: (vars: { week: number; value: number; signal: AbortSignal }) =>
      placeOrder(gameId, vars.week, vars.value, vars.signal),
  });
  useEffect(() => {
    if (sent === null) return;
    const target =
      sent === week ? document.querySelector<HTMLElement>("[data-order-sent]") : document.getElementById(WEEK_HEADING);
    target?.focus();
    setSent(null);
  }, [sent, week]);

  // A read of the envelope after a send, never left hanging (the screen must leave Submitting).
  const reread = () =>
    within(queryClient.refetchQueries({ queryKey: playKey(gameId), exact: true }), ORDER_SUBMIT_TIMEOUT_MS).catch(
      () => undefined,
    );
  /**
   * What the server holds for the Seat's Order of Uke `ordered`, read afresh: `stored` (the open
   * Uke has the Seat's Order, or a later Uke's history shows `value` there), `other` (the Uke
   * moved on with another Order), `none`, or null when the server did not answer in time.
   */
  const stored = async (ordered: number, value: number): Promise<"stored" | "other" | "none" | null> => {
    try {
      await within(
        queryClient.refetchQueries({ queryKey: playKey(gameId), exact: true }, { throwOnError: true }),
        ORDER_SUBMIT_TIMEOUT_MS,
      );
    } catch {
      return null;
    }
    const envelope = queryClient.getQueryData<PlayEnvelope>(playKey(gameId));
    if (!envelope) return null;
    const open = envelope.seat_state.week;
    if (open === ordered) return envelope.turn.order != null ? "stored" : "none";
    if (open < ordered) return "none";
    const row = envelope.seat_state.history.find((w) => w.week === ordered);
    if (!row) return null;
    return row.order === value ? "stored" : "other";
  };

  const confirm = (value: number) => {
    if (inFlight.current) return;
    inFlight.current = true;
    const ordered = week;
    setSending(ordered);
    setOutcome(null);
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setOutcome({ week: ordered, value, kind: "checking" });
      controller.abort();
    }, ORDER_SUBMIT_TIMEOUT_MS);
    const confirmed = () => {
      clearDraft(userId, field);
      setOutcome(null);
      setSent(ordered);
    };
    mutation
      .mutateAsync({ week: ordered, value, signal: controller.signal })
      .then(
        async () => {
          clearTimeout(timer);
          await reread();
          confirmed();
        },
        async (error: unknown) => {
          clearTimeout(timer);
          // An ended session goes to «Logg inn» (the mutation cache); the draft waits there.
          if (isSessionExpired(error)) return;
          const code = errorCode(error);
          // The Seat's Order is stored, maybe from a second device: Confirmed with its value.
          if (code === "order_exists") {
            await reread();
            confirmed();
            return;
          }
          // `week_not_open` too: the api answers it before `order_exists`, so a retry of an Order
          // that arrived and completed the Uke gets it. The history then shows the Order.
          const there = await stored(ordered, value);
          if (there === "stored") confirmed();
          else if (there === "other" || code === "week_not_open") setOutcome({ week: ordered, value, kind: "weekGone" });
          // A lost Seat usually loses the envelope too (403): the code alone says why.
          else if (code === "seat_not_yours") setOutcome({ week: ordered, value, kind: "seatGone" });
          else setOutcome({ week: ordered, value, kind: "failed" });
        },
      )
      .finally(() => {
        inFlight.current = false;
        setSending(null);
      });
  };
  return { sending, outcome, confirm, clear: () => setOutcome(null) };
}

/** The words the order area shows for a send's outcome in Uke `week`. */
function outcomeProps(outcome: SendOutcome | null, week: number) {
  if (!outcome) return { checking: false, failure: null, retry: false };
  const value = formatNumber(outcome.value);
  const here = outcome.week === week;
  switch (outcome.kind) {
    case "checking":
      return { checking: here, failure: null, retry: false };
    case "failed":
      return { checking: false, failure: here ? copy.order.failed : null, retry: here };
    case "weekGone":
      // Read in whichever Uke the screen moved on to.
      return { checking: false, failure: copy.order.weekGone(outcome.week, value), retry: false };
    case "seatGone":
      return { checking: false, failure: here ? copy.order.seatGone(value) : null, retry: false };
  }
}

/**
 * A Guided Week on screen that the Student has not opened yet: tell the api once per Week (Story
 * 6.10, `viewWeek`). A refusal (409: the game moved on, or 403) is left to the next `game:` event,
 * which reads the envelope again; any other failure (offline, a dropped request, a 5xx) is sent
 * again after `VIEW_RETRY_MS`, since the Week waits for this view. Nothing is shown for either.
 */
function useGuidedView(gameId: string, envelope: PlayEnvelope) {
  const sent = useRef(new Set<number>());
  const [attempt, setAttempt] = useState(0);
  const week = envelope.seat_state.week;
  const due = envelope.turn.guided && !envelope.turn.viewed;
  useEffect(() => {
    if (!due || sent.current.has(week)) return;
    sent.current.add(week);
    let retry: ReturnType<typeof setTimeout> | undefined;
    let live = true;
    viewWeek(gameId, week).catch((error: unknown) => {
      const refused = error instanceof ApiRequestError && (error.status === 403 || error.status === 409);
      if (refused || !live) return;
      sent.current.delete(week);
      retry = setTimeout(() => setAttempt((n) => n + 1), VIEW_RETRY_MS);
    });
    return () => {
      live = false;
      if (retry !== undefined) clearTimeout(retry);
    };
  }, [gameId, week, due, attempt]);
}

/** How long a failed view waits before it is sent again. */
const VIEW_RETRY_MS = 5000;

/** Reads the envelope again when it says it changes by time alone (`next_change_at`, AD-8, AD-20):
 * when an AI player's Order falls due. The wait is counted on the server's clock. */
function useRefetchAt(gameId: string, envelope: PlayEnvelope) {
  const queryClient = useQueryClient();
  const due = envelope.next_change_at;
  const from = envelope.server_now;
  useEffect(() => {
    if (!due) return;
    const timer = setTimeout(
      () => void queryClient.invalidateQueries({ queryKey: playKey(gameId), exact: true }),
      Math.max(0, Date.parse(due) - Date.parse(from)),
    );
    return () => clearTimeout(timer);
  }, [queryClient, gameId, due, from]);
}

function NotRunning({ game }: { game: MyGame }) {
  return (
    <>
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      {game.status === "finished" ? (
        <p className={`${LINE} mt-4 text-ink`}>{copy.finished}</p>
      ) : (
        <GameAction game={game} primary />
      )}
      <NotRunningSeats game={game} />
    </>
  );
}

/** «Setene» while the game does not run: who holds each Seat, with no order state. */
function NotRunningSeats({ game }: { game: MyGame }) {
  const now = useServerNow(game.server_now);
  return <GameSeatStatus seats={game.seats} now={now} titleId={`seats-${game.id}`} className="mt-8 max-w-md" />;
}
