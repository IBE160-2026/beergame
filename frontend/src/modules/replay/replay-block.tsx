"use client";

import { useQueryClient } from "@tanstack/react-query";
import NextLink from "next/link";
import { useRouter } from "next/navigation";

import { ActionError } from "@/components/action-error";
import { Button, buttonClassName } from "@/components/button";
import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { useServerNow } from "@/modules/games/seat-status";
import { GameSeatStatus } from "@/modules/games/seat-status-view";
import { gamePath } from "@/modules/identity/homes";
import { enrolledSessionsKey } from "@/modules/sessions/api";

import { type ReplayGame, type StudentReplay, startReplay } from "./api";
import { finishedReplay, replayTitle, resumeWeek } from "./replay";

const copy = nb.homes.student.replay;
const LINE = "text-body-phone text-ink lg:text-body";

/**
 * The Replay on Hjem (Stories 10.3 and 10.4, FR-48, FR-34, UX-DR64), under the Class game once the
 * Student has passed the Debrief quiz. While the api says it may start: «Replay», the consequence
 * line and «Start Replay» (Hjem's primary when `primary`), which makes and starts the Replay at
 * once and opens its play screen, so the Student never meets an empty Seat; a Replay stored but not
 * started shows its Seats above the button. Once started: «Replay · Du er Grossist», its Setene,
 * every AI player «KI-spiller» in text from the first view, and while it runs «Fortsett Replay,
 * Uke 9» to the play screen at its open Uke; once finished, the Lenke «Se Replay» to its end
 * screen (Story 10.5). After the Testfrist with no Replay, nothing shows
 * here; Stegene says the step is not done. The api decides each state (AD-10).
 */
export function ReplayBlock({
  replay,
  sessionId,
  primary,
}: {
  replay: StudentReplay;
  sessionId: string;
  primary: boolean;
}) {
  const titleId = `replay-${sessionId}`;
  if (!replay.game && !replay.can_start) return null;
  const week = resumeWeek(replay);
  return (
    <section aria-labelledby={titleId} className="mt-6 border-t border-hairline pt-4">
      <h3 id={titleId} className="text-step-title font-semibold text-ink">
        {replayTitle(replay)}
      </h3>
      {replay.game && week !== null ? <ResumeAction game={replay.game} week={week} primary={primary} /> : null}
      {replay.game && finishedReplay(replay) ? (
        // Story 10.5: the finished Replay is read again on its screen, which takes no Order.
        <p className="mt-3">
          <Link href={gamePath(replay.game.id)} standalone>
            {copy.view}
          </Link>
        </p>
      ) : null}
      {replay.game ? <ReplaySeats game={replay.game} titleId={`${titleId}-seats`} /> : null}
      {replay.can_start ? <StartAction sessionId={sessionId} primary={primary} /> : null}
    </section>
  );
}

function ReplaySeats({ game, titleId }: { game: ReplayGame; titleId: string }) {
  const now = useServerNow(game.server_now);
  return <GameSeatStatus seats={game.seats} now={now} titleId={titleId} level={4} className="mt-4" />;
}

/** «Fortsett Replay, Uke 9» (Story 10.4): the play screen at the open Uke; Hjem's primary button
 * when no game action is, else a Lenke. */
function ResumeAction({ game, week, primary }: { game: ReplayGame; week: number; primary: boolean }) {
  const label = copy.resume(week);
  if (primary) {
    return (
      <div className="mt-3">
        <NextLink href={gamePath(game.id)} className={buttonClassName("primary")}>
          {label}
        </NextLink>
      </div>
    );
  }
  return (
    <p className="mt-3">
      <Link href={gamePath(game.id)} standalone>
        {label}
      </Link>
    </p>
  );
}

/** «Start Replay» under its consequence line. A started Replay opens its play screen (Story 10.4).
 * A refused start means Hjem was out of date: it is read again. The refusal stays in words under
 * the button while the button shows; once Hjem says the Replay can no longer start (after the
 * Testfrist), Stegene's Replay step says why. */
function StartAction({ sessionId, primary }: { sessionId: string; primary: boolean }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const starting = useAction({
    mutationFn: () => startReplay(sessionId),
    messages: copy.errors,
    fallback: copy.failed,
    onSuccess: (started) => {
      void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
      router.push(gamePath(started.game_id));
    },
  });
  const press = () =>
    starting.mutate(undefined, {
      onError: () => {
        void queryClient.invalidateQueries({ queryKey: enrolledSessionsKey });
      },
    });
  return (
    <div className="mt-3 flex flex-col items-start gap-3">
      <p className={LINE}>{copy.consequence}</p>
      <Button
        variant={primary ? "primary" : "secondary"}
        unavailable={starting.isPending || starting.isSuccess}
        onClick={press}
      >
        {copy.start}
      </Button>
      <ActionError message={starting.errorMessage} />
    </div>
  );
}
