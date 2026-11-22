"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useId } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import {
  classOverviewPath,
  classPath,
  classSessionPath,
  fillSeatsPath,
  HOME_PATH,
  overviewFilledPath,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { classOverviewKey, fillWaitedForSeats, useWaitedForSeats, type WaitedForSeats, waitedForSeatsKey } from "./api";
import { fillFailed, leftOutText, waitingSeatText } from "./fill-seats";

const copy = nb.overview.fill;

/** The shape of a Class session id (a UUID). */
const SESSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * «Sett inn KI-spillere» (Story 8.12, FR-37, UX-DR52, EXPERIENCE.md → Spillstyring → Where): its own
 * page, opened from the Oversikt header's Lenke. It lists the Seats the Class session's games wait
 * for, per game with each Student's name and wait («Spill 2: Noah, 23 t»), the Seats left out for
 * Tilrettelegging («Ikke med (tilrettelegging): Jonas»), the line «Studentene kan ta setene tilbake
 * fra neste Uke.» and the one primary «Sett inn 9 KI-spillere». The press posts the listed Seats
 * and returns to the Oversikt, which reads «9 KI-spillere er satt inn.» with the real count. Browser
 * Back and the crumb return to the Oversikt. Anyone but a Lecturer of the Class sees the
 * permission-denied page (FR-5).
 */
export function FillSeatsPage({ sessionId }: { sessionId: string }) {
  const named = SESSION_ID.test(sessionId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <FillSeatsView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function FillSeatsView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useWaitedForSeats(sessionId);
  const { phase, retry } = usePageState(found, waitedForSeatsKey(sessionId));
  // The waits are counted on the server's clock from the answer's arrival (`server_now`).
  const receivedAt = found.dataUpdatedAt;
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  const crumbs = data
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: data.class_name, href: classPath(data.class_id) },
        { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
        { label: nb.overview.crumb, href: classOverviewPath(sessionId) },
        { label: copy.crumb, href: fillSeatsPath(sessionId) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={data ? copy.title : undefined}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 4, columns: 1 }}
    >
      {data ? (
        <FillList
          sessionId={sessionId}
          data={data}
          now={Date.parse(data.server_now) + Math.max(0, Date.now() - receivedAt)}
        />
      ) : null}
    </PageShell>
  );
}

function FillList({ sessionId, data, now }: { sessionId: string; data: WaitedForSeats; now: number }) {
  const id = useId();
  const lineId = `${id}-line`;
  const router = useRouter();
  const queryClient = useQueryClient();
  const games = data.games;
  const seatIds = games.flatMap((game) => game.seats.map((seat) => seat.seat_id));
  const leftOut = leftOutText(data.left_out);
  const send = useAction({
    mutationFn: async (ids: string[]) => {
      const answer = await fillWaitedForSeats(sessionId, ids);
      if (fillFailed(answer)) throw new Error("fill failed");
      return answer;
    },
    fallback: copy.failed,
    onSuccess: (answer) => {
      void queryClient.invalidateQueries({ queryKey: classOverviewKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: waitedForSeatsKey(sessionId) });
      // Back from the Oversikt leads where the Lecturer came from, not to this page again.
      router.replace(overviewFilledPath(sessionId, answer.inserted));
    },
  });
  const leftOutLine = leftOut ? (
    <p className="text-body-phone text-ink-secondary [overflow-wrap:anywhere] lg:text-body" data-fill-left-out="">
      {leftOut}
    </p>
  ) : null;
  if (seatIds.length === 0) {
    return (
      <div className="mt-6 flex max-w-[40rem] flex-col gap-3">
        <p className="text-body-phone text-ink lg:text-body">{copy.empty}</p>
        {leftOutLine}
      </div>
    );
  }
  return (
    <div className="mt-6 flex max-w-[40rem] flex-col gap-6" data-fill-seats-page="">
      <section aria-labelledby={id}>
        <h2 id={id} className="border-b border-axis pb-2 text-label text-ink tabular-nums lining-nums">
          {copy.listLabel} {seatIds.length}
        </h2>
        <ul>
          {games.map((game) => {
            const name = nb.overview.game(game.game_number ?? null);
            return (
              <li
                key={game.game_id}
                data-game={game.game_id}
                className="grid grid-cols-1 gap-y-1 border-b border-hairline py-3 sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-x-6"
              >
                <p className="text-label text-ink">{name}</p>
                <ul
                  aria-label={nb.overview.seatsLabel(name)}
                  className="flex flex-wrap gap-x-4 text-body-phone text-ink-secondary tabular-nums lining-nums lg:text-body"
                >
                  {game.seats.map((seat) => (
                    <li key={seat.seat_id} data-seat={seat.seat_id} className="[overflow-wrap:anywhere]">
                      {waitingSeatText(seat, now)}
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      </section>
      <div className="flex flex-col items-start gap-3">
        {leftOutLine}
        <p id={lineId} className="text-body-phone text-ink lg:text-body" data-fill-consequence="">
          {copy.consequence}
        </p>
        <Button
          variant="primary"
          data-fill-confirm=""
          className="w-full lg:w-auto"
          aria-describedby={lineId}
          unavailable={send.isPending || send.isSuccess}
          onClick={() => send.mutate(seatIds)}
        >
          {copy.confirm(seatIds.length)}
        </Button>
        <ActionError message={send.errorMessage} />
      </div>
    </div>
  );
}
