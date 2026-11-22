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
  HOME_PATH,
  overviewStartedPath,
  startGamesPath,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { classOverviewKey, type StartGames, startGames, startGamesKey, useStartGames } from "./api";
import { seatTexts } from "./overview";
import { confirmText } from "./start-games";

const copy = nb.overview.start;

/** The shape of a Class session id (a UUID). */
const SESSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * «Start spill» (Story 8.10, FR-22, UX-DR52, EXPERIENCE.md → Spillstyring → Where): its own page,
 * opened from the Oversikt header's Lenke. It lists the Class games that have not started and may
 * start now, as the Oversikt words them, the line «Spillene starter for alle i dem. Reglene for
 * ventetid gjelder fra nå.» and the one primary «Start 12 spill». The press starts the listed games
 * and returns to the Oversikt, which reads «12 spill er startet.» with the real count. Browser Back
 * and the crumb return to the Oversikt. Anyone but a Lecturer of the Class sees the
 * permission-denied page (FR-5).
 */
export function StartGamesPage({ sessionId }: { sessionId: string }) {
  const named = SESSION_ID.test(sessionId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <StartGamesView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function StartGamesView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useStartGames(sessionId);
  const { phase, retry } = usePageState(found, startGamesKey(sessionId));
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
        { label: copy.crumb, href: startGamesPath(sessionId) },
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
      {data ? <StartList sessionId={sessionId} data={data} /> : null}
    </PageShell>
  );
}

function StartList({ sessionId, data }: { sessionId: string; data: StartGames }) {
  const id = useId();
  const lineId = `${id}-line`;
  const router = useRouter();
  const queryClient = useQueryClient();
  const games = data.games;
  const send = useAction({
    mutationFn: (ids: string[]) => startGames(sessionId, ids),
    fallback: copy.failed,
    onSuccess: (answer) => {
      void queryClient.invalidateQueries({ queryKey: classOverviewKey(sessionId) });
      void queryClient.invalidateQueries({ queryKey: startGamesKey(sessionId) });
      // Back from the Oversikt leads where the Lecturer came from, not to this page again.
      router.replace(overviewStartedPath(sessionId, answer.started));
    },
  });
  if (games.length === 0) {
    return <p className="mt-6 max-w-[40rem] text-body-phone text-ink lg:text-body">{copy.empty}</p>;
  }
  return (
    <div className="mt-6 flex max-w-[40rem] flex-col gap-6" data-start-games="">
      <section aria-labelledby={id}>
        <h2 id={id} className="border-b border-axis pb-2 text-label text-ink tabular-nums lining-nums">
          {copy.listLabel} {games.length}
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
                  className="flex flex-wrap gap-x-4 text-body-phone text-ink-secondary lg:text-body"
                >
                  {seatTexts(game).map((text, index) => (
                    <li key={game.seats[index]!.role} className="[overflow-wrap:anywhere]">
                      {text}
                    </li>
                  ))}
                </ul>
              </li>
            );
          })}
        </ul>
      </section>
      <div className="flex flex-col items-start gap-3">
        <p id={lineId} className="text-body-phone text-ink lg:text-body" data-start-games-consequence="">
          {copy.consequence}
        </p>
        <Button
          variant="primary"
          data-start-games-confirm=""
          className="w-full lg:w-auto"
          aria-describedby={lineId}
          unavailable={send.isPending || send.isSuccess}
          onClick={() => send.mutate(games.map((game) => game.game_id))}
        >
          {confirmText(games.length)}
        </Button>
        <ActionError message={send.errorMessage} />
      </div>
    </div>
  );
}
