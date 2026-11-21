"use client";

import { useEffect, useId, useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classOverviewPath, classPath, classSessionPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { osloDateText } from "@/modules/sessions/dates";

import { type ClassOverview, classOverviewKey, type OverviewGame, useClassOverview } from "./api";
import { clockWithSeconds, costText, groupsOf, headline, type OverviewGroup, seatTexts, waitLines } from "./overview";

const copy = nb.overview;

/** The shape of a Class session id (a UUID). */
const SESSION_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** How often the wait durations are counted again while the page is open. */
const TICK_MS = 30_000;

/**
 * The Oversikt (Story 7.1, FR-39, UX-DR40): every Class game of a Class session, grouped by status
 * with the headline counts and «Oppdatert hh:mm:ss», each row with its game number, Uke, whom it
 * waits for and how long, its four Seats and the chain's cost so far. Before the Start date it
 * lists the allocation only. Everything comes from the api's maintained summaries; the page only
 * groups, sorts and words them (AD-10). Anyone but the Class's staff sees the permission-denied
 * page (FR-5).
 */
export function OverviewPage({ sessionId }: { sessionId: string }) {
  const named = SESSION_ID.test(sessionId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <OverviewView sessionId={sessionId} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function OverviewView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useClassOverview(sessionId);
  const { phase, retry } = usePageState(found, classOverviewKey(sessionId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  const crumbs = data
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: data.class_name, href: classPath(data.class_id) },
        { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
        { label: copy.crumb, href: classOverviewPath(sessionId) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 8, columns: 4 }}
      header={data ? <OverviewHeader data={data} /> : undefined}
    >
      {data ? <OverviewBody data={data} receivedAt={found.dataUpdatedAt} /> : null}
    </PageShell>
  );
}

function OverviewHeader({ data }: { data: ClassOverview }) {
  return (
    <header className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
      <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
      <p className="text-body-phone text-ink-secondary [overflow-wrap:anywhere] lg:text-body">
        {copy.session(data.session_number, data.class_name)}
      </p>
    </header>
  );
}

/** The server's clock now: `server_now` plus the time since the answer arrived, counted again
 * every `TICK_MS`. The browser's clock only measures the time between. */
function useServerNow(serverNow: string, receivedAt: number): number {
  const [, setTick] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setTick((tick) => tick + 1), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);
  return Date.parse(serverNow) + Math.max(0, Date.now() - receivedAt);
}

function OverviewBody({ data, receivedAt }: { data: ClassOverview; receivedAt: number }) {
  const now = useServerNow(data.server_now, receivedAt);
  if (data.before_start) return <Allocation data={data} />;
  const groups = groupsOf(data.items);
  return (
    <div className="mt-6">
      <p className="text-body-phone font-semibold text-ink tabular-nums lining-nums lg:text-body">
        {headline(data.counts)}
      </p>
      <p className="mt-1 text-caption text-ink-secondary tabular-nums lining-nums">
        {copy.updated(clockWithSeconds(Date.parse(data.server_now)))}
      </p>
      {groups.length === 0 ? (
        <p className="mt-8 text-body-phone text-ink lg:text-body">{copy.empty}</p>
      ) : (
        groups.map((group) => <Group key={group.name} group={group} now={now} />)
      )}
    </div>
  );
}

function Group({ group, now }: { group: OverviewGroup; now: number }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="mt-8 max-w-5xl">
      <h2 id={id} className="border-b border-axis pb-2 text-label text-ink tabular-nums lining-nums">
        {group.title} {group.games.length}
      </h2>
      <ul>
        {group.games.map((game) => (
          <GameRow key={game.game_id} game={game} now={now} />
        ))}
      </ul>
    </section>
  );
}

function GameRow({ game, now }: { game: OverviewGame; now: number }) {
  const name = copy.game(game.game_number ?? null);
  const cost = costText(game);
  const waits = waitLines(game, now);
  return (
    <li
      data-game={game.game_id}
      className="grid grid-cols-1 gap-y-1 border-b border-hairline py-3 lg:grid-cols-[7rem_5rem_minmax(0,1fr)_10rem] lg:gap-x-6"
    >
      <p className="text-label text-ink">{name}</p>
      <p className="text-body-phone text-ink-secondary tabular-nums lining-nums lg:text-body">
        {game.week != null ? copy.week(game.week) : null}
      </p>
      <div className="min-w-0">
        {waits.map((line) => (
          <p key={line} className="text-body-phone font-semibold text-ink lg:text-body">
            {line}
          </p>
        ))}
        <Seats game={game} label={copy.seatsLabel(name)} />
      </div>
      <p className="text-body-phone text-ink tabular-nums lining-nums lg:text-right lg:text-body">
        {cost ? (
          <>
            <span className="text-ink-secondary lg:sr-only">{copy.chainCost} </span>
            {cost}
          </>
        ) : null}
      </p>
    </li>
  );
}

function Seats({ game, label }: { game: OverviewGame; label: string }) {
  return (
    <ul aria-label={label} className="flex flex-wrap gap-x-4 text-body-phone text-ink-secondary lg:text-body">
      {seatTexts(game).map((text, index) => (
        <li key={game.seats[index]!.role} className="[overflow-wrap:anywhere]">
          {text}
        </li>
      ))}
    </ul>
  );
}

/** Before the Start date: the allocation, game by game, with no Week and no cost (Story 7.1). */
function Allocation({ data }: { data: ClassOverview }) {
  const id = useId();
  const games = [...data.items].sort((a, b) => (a.game_number ?? 0) - (b.game_number ?? 0));
  return (
    <section aria-labelledby={id} className="mt-6 max-w-5xl">
      <p className="text-body-phone text-ink lg:text-body">
        {data.start_at ? copy.beforeStart.startsAt(osloDateText(data.start_at)) : copy.beforeStart.noDate}
      </p>
      <h2 id={id} className="mt-8 border-b border-axis pb-2 text-label text-ink tabular-nums lining-nums">
        {copy.beforeStart.title} {games.length}
      </h2>
      {games.length === 0 ? (
        <p className="mt-4 text-body-phone text-ink lg:text-body">{copy.beforeStart.empty}</p>
      ) : (
        <ul>
          {games.map((game) => {
            const name = copy.game(game.game_number ?? null);
            return (
              <li
                key={game.game_id}
                data-game={game.game_id}
                className="grid grid-cols-1 gap-y-1 border-b border-hairline py-3 lg:grid-cols-[7rem_minmax(0,1fr)] lg:gap-x-6"
              >
                <p className="text-label text-ink">{name}</p>
                <Seats game={game} label={copy.seatsLabel(name)} />
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
