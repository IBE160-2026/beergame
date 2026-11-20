"use client";

import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { Stegene } from "@/components/stegene";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { enrolledClassesKey, useEnrolledClasses } from "@/modules/classes/api";
import { seatChoicePath } from "@/modules/identity/homes";
import { type EnrolledSession, enrolledSessionsKey, useEnrolledSessions } from "@/modules/sessions/api";
import { homeLine } from "@/modules/sessions/seat-choice";
import { roleName } from "@/modules/sessions/sessions";

import { deadlineText, gameTitle, holderText, labHourText, stepItems } from "./home";

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
  return (
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
              own.map((session) => <SessionBlock key={session.id} session={session} labelled={own.length > 1} />)
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** One Class session on Hjem: the game card or the line before it, then Stegene and the dates. */
function SessionBlock({ session, labelled }: { session: EnrolledSession; labelled: boolean }) {
  const game = session.game ?? null;
  const deadline = deadlineText(session);
  const labs = session.lab_hours ?? [];
  return (
    <div className="mt-4 first-of-type:mt-2">
      {labelled || session.obligatory ? (
        <p className="text-label text-ink-secondary">
          {[labelled ? copy.session(session.number) : null, session.obligatory ? copy.obligatory : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
      ) : null}
      {game ? <GameCard game={game} session={session} /> : <BeforeStart session={session} />}
      <Stegene title={copy.steps} titleId={`steps-${session.id}`} items={stepItems(session.steps)} />
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

/** «Spill 17 · Du er Grossist» and «Setene»: each Seat's Role and who holds it, in words. */
function GameCard({ game, session }: { game: NonNullable<EnrolledSession["game"]>; session: EnrolledSession }) {
  const seatsId = `seats-${session.id}`;
  const drawn = homeLine(session);
  return (
    <div className="mt-2">
      <h3 className="text-step-title font-semibold text-ink">{gameTitle(game)}</h3>
      {/* Story 5.17: a Student the lock drew a Seat for is told so under the game. */}
      {drawn?.kind === "drawn" ? (
        <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{drawn.text}</p>
      ) : null}
      <section aria-labelledby={seatsId} className="mt-4">
        <h4 id={seatsId} className="text-label font-semibold text-ink">
          {copy.seats}
        </h4>
        <ul className="mt-2 flex flex-col gap-1">
          {game.seats.map((seat) => (
            <li key={seat.role} className="flex flex-wrap gap-x-4 text-body-phone lg:text-body">
              <span className="min-w-[6.5rem] text-ink">{roleName(seat.role)}</span>
              <span className={seat.holder === "student" ? "break-words text-ink" : "text-ink-secondary"}>
                {holderText(seat)}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
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
