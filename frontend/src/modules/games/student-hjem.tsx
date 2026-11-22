"use client";

import NextLink from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button, buttonClassName } from "@/components/button";
import { GameCard } from "@/components/game-card";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { Stegene } from "@/components/stegene";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { enrolledClassesKey, useEnrolledClasses } from "@/modules/classes/api";
import { ASSESSMENT_PATH, gamePath, rulesPath, seatChoicePath } from "@/modules/identity/homes";
import { MyMessages } from "@/modules/messaging/my-messages";
import { type EnrolledSession, enrolledSessionsKey, useEnrolledSessions } from "@/modules/sessions/api";
import { ownLines } from "@/modules/reports/adjustment";
import { ReplayBlock } from "@/modules/replay/replay-block";
import { wantsReplayPrimary } from "@/modules/replay/replay";
import { homeLine } from "@/modules/sessions/seat-choice";

import { GameAction } from "./game-action";
import {
  assessmentReady,
  cardState,
  deadlineText,
  gameTitle,
  labHourText,
  type NextAction,
  netSentence,
  nextAction,
  stepItems,
  testHandedIn,
  toWeekText,
} from "./home";
import { InRoomLine } from "./in-room-view";
import { ownSeatTakenOver, useServerNow } from "./seat-status";
import { PauseControl, PauseLine } from "./pause-view";
import { GameSeatStatus, TakenOverNote } from "./seat-status-view";
import { TimeProposalBlock } from "./time-proposal-view";
import { MiniWeekTable } from "./week-table-view";

/** The next actions that are a control; «not ready» is a line only. */
const PRIMARY_ACTIONS: ReadonlySet<NextAction> = new Set(["rules", "start", "play"]);

type StudentGame = NonNullable<EnrolledSession["game"]>;

/** Whether the game asks for Hjem's one primary button: its next action is a control, except a
 * game the Student has ordered in, whose Spillkort has no primary action (Story 6.17, UX-DR28), and
 * a game the Play deadline playout took over, which waits for nothing from them (Story 8.14). */
function wantsPrimary(game: StudentGame): boolean {
  return (
    PRIMARY_ACTIONS.has(nextAction(game)) &&
    cardState(game) !== "ordered" &&
    !ownSeatTakenOver(game.seats) &&
    !(game.status === "running" && game.played_out)
  );
}

const copy = nb.homes.student;

/**
 * Hjem, the Student hub (Story 6.1, UX-DR29, UX-DR62, mockup `04-student-hjem.png`): each Class
 * the Student is in, and under it each of its Class sessions. From the Start date a session shows
 * the Student's Class game («Spill 17 · Du er Grossist») and «Setene», Fabrikk first, every AI
 * player as «KI-spiller» in text; before it, also after a confirmed allocation, the line «Du får
 * Rolle og spill på startdatoen.» (or Story 5.17's «Velg spill og sete» Lenke or drawn line).
 * Then Stegene, «Neste frist», the upcoming Labtimer and the Obligatorisk mark, all from
 * `/api/me/class-sessions`. The page waits for both reads with the Skjelett, and a failed read
 * shows the page-error line with «Prøv igjen» (Story 3.4).
 */
export function StudentHjem() {
  const classes = useEnrolledClasses();
  const sessions = useEnrolledSessions();
  const classState = usePageState(classes, enrolledClassesKey);
  const sessionState = usePageState(sessions, enrolledSessionsKey);
  // Story 6.19: while a «Foreslå tidspunkt» form is open its send is the primary, so the game's
  // own primary action steps back and Hjem keeps one primary button.
  const [proposing, setProposing] = useState<ReadonlySet<string>>(new Set());
  const phases = [classState.phase, sessionState.phase];

  if (phases.includes("failed")) {
    const retry = () => {
      if (classState.phase === "failed") classState.retry();
      if (sessionState.phase === "failed") sessionState.retry();
    };
    return (
      <div className="mt-8 flex flex-col items-start gap-3">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button onClick={retry}>{nb.system.retry}</Button>
      </div>
    );
  }
  if (phases.some((phase) => phase === "loading" || phase === "slow")) {
    return (
      <div className="mt-8">
        <Skeleton heading rows={4} />
        <LoadingNote visible={phases.includes("slow")} />
      </div>
    );
  }

  const items = classes.data?.items ?? [];
  if (items.length === 0) {
    return <p className="mt-8 max-w-md text-body-phone text-ink-secondary lg:text-body">{nb.homes.noClass}</p>;
  }
  const all = sessions.data?.items ?? [];
  // Hjem keeps one primary button (UX-DR8): the next action («Les reglene», «Start spillet» or
  // «Gå til Uke n», Story 6.5) of the first game that has one, in the order the page lists them;
  // any further one is a Lenke or a secondary button.
  const listed = items.flatMap((item) => all.filter((session) => session.class_id === item.id));
  const primaryGame =
    listed.find((session) => (session.game ? wantsPrimary(session.game) : false))?.id ?? null;
  // Story 10.3: «Start Replay» is the primary only when no game action is.
  const primaryReplay =
    primaryGame === null ? (listed.find((session) => wantsReplayPrimary(session.replay))?.id ?? null) : null;
  return (
    <>
      <ul className="mt-8 flex max-w-md flex-col border-t border-hairline">
        {items.map((item) => {
          const own = all.filter((session) => session.class_id === item.id);
          return (
            <li key={item.id} className="border-b border-hairline py-5">
              <h2 className="text-headline text-ink [overflow-wrap:anywhere]">
                {nb.classes.home.label(item.name, item.course_code)}
              </h2>
              {own.length === 0 ? (
                <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{nb.homes.startDate}</p>
              ) : (
                own.map((session) => (
                  <SessionBlock
                    key={session.id}
                    session={session}
                    labelled={own.length > 1}
                    primary={session.id === primaryGame && proposing.size === 0}
                    replayPrimary={session.id === primaryReplay && proposing.size === 0}
                    onProposing={(open) =>
                      setProposing((was) => {
                        if (was.has(session.id) === open) return was;
                        const next = new Set(was);
                        if (open) next.add(session.id);
                        else next.delete(session.id);
                        return next;
                      })
                    }
                  />
                ))
              )}
            </li>
          );
        })}
      </ul>
      {/* Story 7.10: the Messages from the staff, after the Classes, so the game's one primary
          action stays first (UX-DR8). */}
      <MyMessages showClass={items.length > 1} />
    </>
  );
}

/** One Class session on Hjem: the game card or the line before it, then Stegene and the dates. */
function SessionBlock({
  session,
  labelled,
  primary,
  replayPrimary,
  onProposing,
}: {
  session: EnrolledSession;
  labelled: boolean;
  primary: boolean;
  replayPrimary: boolean;
  onProposing: (open: boolean) => void;
}) {
  const game = session.game ?? null;
  const deadline = deadlineText(session);
  const labs = session.lab_hours ?? [];
  return (
    <div className="mt-2 not-first-of-type:mt-6 not-first-of-type:border-t not-first-of-type:border-hairline not-first-of-type:pt-4">
      {labelled || session.obligatory ? (
        <p className="text-label text-ink-secondary">
          {[labelled ? copy.session(session.number) : null, session.obligatory ? copy.obligatory : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
      ) : null}
      {game ? (
        <GameBlock game={game} session={session} primary={primary} onProposing={onProposing} />
      ) : (
        <BeforeStart session={session} />
      )}
      {/* Story 10.3: the Replay, once the Debrief quiz is passed. */}
      {session.replay ? <ReplayBlock replay={session.replay} sessionId={session.id} primary={replayPrimary} /> : null}
      <Stegene title={copy.steps} titleId={`steps-${session.id}`} items={stepItems(session.steps, session.id, session.replay)} />
      {/* Story 12.2: the «KI-vurdering» once the test is handed in; the page says whether it is ready.
          Story 12.4: once it is ready Hjem says so, live through `user:<id>`. */}
      {testHandedIn(session.steps) ? (
        <p
          className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1"
          aria-live="polite"
          data-assessment-ready={assessmentReady(session.steps) ? "" : undefined}
        >
          {assessmentReady(session.steps) ? (
            <span className="text-body-phone text-ink lg:text-body">{nb.assessment.student.readyOnHjem}</span>
          ) : null}
          <Link href={ASSESSMENT_PATH(session.id)} standalone>
            {nb.assessment.student.link}
          </Link>
        </p>
      ) : null}
      {/* The Student's own Tilrettelegging (Story 8.9): only they read it. */}
      {ownLines(session.adjustment).length > 0 ? (
        <div className="mt-3 flex flex-col gap-1 text-body-phone text-ink-secondary lg:text-body" data-own-adjustment="">
          {ownLines(session.adjustment).map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      ) : null}
      {deadline || labs.length > 0 ? (
        <dl className="mt-6 flex flex-col gap-2 border-t border-hairline pt-4 text-body-phone lg:text-body">
          {deadline ? (
            <div className="flex flex-wrap justify-between gap-x-4">
              <dt className="text-ink-secondary">{copy.nextDeadline}</dt>
              <dd className="font-semibold text-ink">{deadline}</dd>
            </div>
          ) : null}
          {labs.map((lab) => (
            <div key={lab.id} className="flex flex-wrap justify-between gap-x-4">
              <dt className="text-ink-secondary">{copy.labHour}</dt>
              <dd className="text-ink [overflow-wrap:anywhere]">{labHourText(lab)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

/** «Spill 17 · Du er Grossist», while the game runs its Spillkort (Story 6.17), and «Setene»: each
 * Seat's Role, who holds it and, while the game runs, whether it has ordered this Uke and how long
 * the game has waited for it (Story 6.14), then the proposed time to play (Story 6.19). The Spillkort holds the game's action and stands above
 * Setene, as in `04-student-hjem.png`; without it the action stays under Setene. */
function GameBlock({
  game,
  session,
  primary,
  onProposing,
}: {
  game: StudentGame;
  session: EnrolledSession;
  primary: boolean;
  onProposing: (open: boolean) => void;
}) {
  const seatsId = `seats-${session.id}`;
  const now = useServerNow(game.server_now);
  const drawn = homeLine(session);
  const card = cardState(game);
  // A finished game waits for no one: its Seats show no status, and the rules are behind it.
  const finished = game.status === "finished";
  const seats = finished ? game.seats.map((seat) => ({ ...seat, ordered: null })) : game.seats;
  // An open «Foreslå tidspunkt» form or Pausevalg (Story 8.6) has its own primary: Hjem's steps back.
  const [forms, setForms] = useState({ proposal: false, pause: false });
  const formOpen = forms.proposal || forms.pause;
  const told = useRef(onProposing);
  useEffect(() => {
    told.current = onProposing;
  });
  // Told on every change, and `false` when the block goes, so Hjem's primary never stays stepped back.
  useEffect(() => {
    told.current(formOpen);
    return () => told.current(false);
  }, [formOpen]);
  return (
    <div className="mt-2">
      <h3 className="text-step-title font-semibold text-ink">{gameTitle(game)}</h3>
      {/* Story 5.17: a Student the lock drew a Seat for is told so under the game. */}
      {drawn?.kind === "drawn" ? (
        <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{drawn.text}</p>
      ) : null}
      {card && game.seat_state ? (
        <PlayCard game={game} state={game.seat_state} card={card} primary={primary} titleId={`card-${session.id}`} />
      ) : null}
      {/* Story 8.2: an AI player took the Student's Seat over while the game runs. */}
      {game.status === "running" && !game.played_out && ownSeatTakenOver(game.seats) ? (
        <TakenOverNote obligatory={game.obligatory} gameId={game.id} seats={game.seats} className="mt-4" />
      ) : null}
      {/* Story 8.6: the pause line above Setestatus, as on the play screen. */}
      {finished ? null : <PauseLine gameId={game.id} pause={game.pause} className="mt-4" />}
      {/* Story 8.11: the «I rommet» line above Setestatus, as on Spill (Epic 8 close-out). */}
      {finished ? null : <InRoomLine inRoom={game.in_room} className="mt-4" />}
      {/* Story 6.14: the Setestatus, as on the play screen. */}
      <GameSeatStatus gameId={game.id} seats={seats} now={now} titleId={seatsId} level={4} className="mt-4" />
      {/* Story 8.6: «Ta pause» under Setestatus, and the Pausevalg in place. */}
      <PauseControl
        gameId={game.id}
        canPause={game.can_pause ?? false}
        onFormOpen={(open) => setForms((was) => (was.pause === open ? was : { ...was, pause: open }))}
        className="mt-4"
      />
      {/* Story 6.19: the proposed time to play, and «Foreslå tidspunkt» while the game is not over;
          after the Play deadline playout took it over, none (Story 8.14). */}
      {game.played_out ? null : (
        <TimeProposalBlock
          game={game}
          now={now}
          playDeadline={session.play_deadline ?? null}
          onFormOpen={(open) => setForms((was) => (was.proposal === open ? was : { ...was, proposal: open }))}
          className="mt-4"
        />
      )}
      {card ? null : <GameAction game={game} primary={primary} />}
      {/* Story 6.2: once the briefing no longer comes first, it stays a Lenke. */}
      {game.briefing_first || finished ? null : (
        <p className="mt-3">
          <Link href={rulesPath(game.id)} standalone>
            {copy.rulesLink}
          </Link>
        </p>
      )}
    </div>
  );
}

/**
 * The Spillkort of a running game (Story 6.17, FR-25, UX-DR28): «Spillet venter på deg» with the
 * one primary «Gå til Uke 11», or, once the Student has ordered, the draft title and «Gå til Uke 11»
 * as a Lenke only. The numbers are the api's `seat_state`, the play screen's own source (AD-3).
 */
function PlayCard({
  game,
  state,
  card,
  primary,
  titleId,
}: {
  game: StudentGame;
  state: NonNullable<StudentGame["seat_state"]>;
  card: "waitsForYou" | "ordered";
  primary: boolean;
  titleId: string;
}) {
  const href = gamePath(game.id);
  const label = toWeekText({ week: state.week });
  const action =
    card === "waitsForYou" && primary ? (
      <NextLink href={href} className={buttonClassName("primary")}>
        {label}
      </NextLink>
    ) : (
      <Link href={href} standalone>
        {label}
      </Link>
    );
  return (
    <GameCard
      className="mt-4"
      title={card === "waitsForYou" ? copy.card.waitsForYou : copy.card.ordered}
      titleId={titleId}
      week={copy.card.week(state.week)}
      figure={
        <MiniWeekTable state={state} nowOrder={game.turn?.order ?? undefined} label={copy.card.region(game.number)} />
      }
      total={copy.card.total(formatNumber(state.total_cost, { kroner: true }))}
      summary={netSentence(state)}
      action={action}
    />
  );
}

/** Before the Start date, or with no Seat yet: «Du får Rolle og spill på startdatoen.», or while
 * the Class session lets the Students choose, Story 5.17's Lenke, or the Seat the draw gave. */
function BeforeStart({ session }: { session: EnrolledSession }) {
  const line = homeLine(session);
  if (line?.kind === "open") {
    return (
      <div className="mt-1 flex flex-col items-start">
        <p className="text-body-phone text-ink-secondary lg:text-body">{nb.sessions.seatChoice.openLine}</p>
        <Link href={seatChoicePath(session.id)} standalone>
          {nb.sessions.seatChoice.open}
        </Link>
      </div>
    );
  }
  if (line?.kind === "drawn") {
    return <p className="mt-1 text-body-phone text-ink lg:text-body">{line.text}</p>;
  }
  return <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{nb.homes.startDate}</p>;
}
