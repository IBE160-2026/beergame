"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/button";
import { Link } from "@/components/link";
import type { LiveLines } from "@/components/connection-notice";
import { Switch } from "@/components/switch";
import { nb } from "@/copy/nb";
import { useThrottledAnnouncement } from "@/lib/announce";
import { ApiRequestError } from "@/lib/api/client";
import { formatClock } from "@/lib/connection";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import {
  classOverviewPath,
  classPath,
  classSessionPath,
  gameInsightPath,
  HOME_PATH,
  messagePath,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { osloDateText } from "@/modules/sessions/dates";

import { type ClassOverview, classOverviewKey, type OverviewAnswer, type OverviewGame, useClassOverview } from "./api";
import { OverviewRail } from "./overview-rail";
import { OverviewWall, rememberReturn, type ReturnTo } from "./overview-wall";
import {
  changedGames,
  clockWithSeconds,
  readAgainAt,
  costText,
  groupsOf,
  headline,
  type OverviewGroup,
  seatTexts,
  waitLines,
} from "./overview";

const copy = nb.overview;
const live = copy.live;

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
  // «Oppdater automatisk» (Story 7.5): on, the page shows each answer as it arrives; off, it holds
  // the answer it showed when switched off while the query goes on reading, and «Oppdater» moves
  // the held answer to the latest. Page state only.
  const [auto, setAuto] = useState(true);
  const [held, setHeld] = useState<OverviewAnswer | null>(null);
  const latest = found.data;
  useReadAt(sessionId, latest);
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const shown = latest && !auto && held && !latest.overview.before_start ? held : latest;
  const data = shown?.overview;
  const crumbs = data
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: data.class_name, href: classPath(data.class_id) },
        { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
        { label: copy.crumb, href: classOverviewPath(sessionId) },
      ] as const)
    : undefined;
  // A background read that failed leaves the last answer on screen, said so in the line with the
  // time of the last read that succeeded (a 304 included); it is tried again by itself too.
  const readFailed = Boolean(latest) && found.isError && !found.isFetching;
  const liveLines: LiveLines = {
    stale: live.stale,
    staleAction: { label: live.reload, onPress: () => window.location.reload() },
    failed: readFailed
      ? { message: live.failed(formatClock(found.dataUpdatedAt)), action: { label: nb.system.retry, onPress: retry } }
      : undefined,
  };
  const switchAuto = (on: boolean) => {
    setAuto(on);
    setHeld(on ? null : (latest ?? null));
  };
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 8, columns: 4 }}
      header={data ? <OverviewHeader data={data} sessionId={sessionId} /> : undefined}
      liveLines={liveLines}
    >
      {shown && latest ? (
        <OverviewBody
          sessionId={sessionId}
          answer={shown}
          live={{
            auto,
            onAuto: switchAuto,
            changes: held && !auto ? changedGames(held.overview, latest.overview, held === latest) : 0,
            heldAt: held && !auto ? held : null,
            onApply: () => setHeld(latest),
          }}
        />
      ) : null}
    </PageShell>
  );
}

/** How many more reads follow a timed one while the answer stays the same (the api's clock may
 * pass the moment a little later than ours measured). */
const READ_AGAIN_TIMES = 6;
const READ_AGAIN_MS = 5_000;
/** The longest a timer is set for at once: a longer wait is measured again in steps. */
const LONGEST_TIMER_MS = 24 * 60 * 60 * 1000;

/**
 * Reads the Oversikt again at the answer's `next_change_at` (the Start date while it has not
 * passed, Story 7.5, AD-8): the wait is `next_change_at − server_now` counted from the answer's
 * arrival, so the browser's clock only measures it and never decides a status. While the answer
 * stays the same after that, it is read a few more times.
 */
function useReadAt(sessionId: string, answer: OverviewAnswer | undefined) {
  const queryClient = useQueryClient();
  const next = answer?.overview.next_change_at;
  const serverNow = answer?.overview.server_now;
  const receivedAt = answer?.receivedAt;
  useEffect(() => {
    if (!next || !serverNow || receivedAt === undefined) return;
    const due = readAgainAt(next, serverNow, receivedAt);
    let timer: number | undefined;
    let again = 0;
    const read = () =>
      void queryClient.invalidateQueries({
        queryKey: classOverviewKey(sessionId),
      });
    const wait = () => {
      const left = due - Date.now();
      if (left > 0) {
        timer = window.setTimeout(wait, Math.min(left, LONGEST_TIMER_MS));
        return;
      }
      read();
      if (again++ < READ_AGAIN_TIMES) timer = window.setTimeout(wait, READ_AGAIN_MS);
    };
    wait();
    return () => window.clearTimeout(timer);
  }, [queryClient, sessionId, next, serverNow, receivedAt]);
}

function OverviewHeader({ data, sessionId }: { data: ClassOverview; sessionId: string }) {
  return (
    <header className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
      <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
      <p className="text-body-phone text-ink-secondary [overflow-wrap:anywhere] lg:text-body">
        {copy.session(data.session_number, data.class_name)}
      </p>
      {/* A Message to every registered Student of the Class session (Story 7.9); worded unlike
          the Varselbånd's «Send Melding». */}
      <Link href={messagePath(sessionId)} data-message-session="" standalone>
        {nb.messages.toSession}
      </Link>
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

type LiveControls = {
  auto: boolean;
  onAuto: (on: boolean) => void;
  /** Changes waiting while held; 0 when none or when on. */
  changes: number;
  /** The held answer while «Oppdater automatisk» is off. */
  heldAt: OverviewAnswer | null;
  onApply: () => void;
};

function OverviewBody({
  sessionId,
  answer,
  live: controls,
}: {
  sessionId: string;
  answer: OverviewAnswer;
  live: LiveControls;
}) {
  const data = answer.overview;
  const now = useServerNow(data.server_now, answer.receivedAt);
  const returnTo = useReturnTo(sessionId);
  const counts = headline(data.counts);
  // The headline counts, read out politely at most once a minute (UX-DR44); nothing else here is.
  const said = useThrottledAnnouncement(data.before_start ? "" : counts);
  const groups = groupsOf(data.items);
  if (data.before_start) {
    return (
      <RailLayout rail={<OverviewRail data={data} groups={groups} now={now} />}>
        <Allocation data={data} sessionId={sessionId} />
      </RailLayout>
    );
  }
  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-start justify-between gap-x-8 gap-y-4">
        <div className="min-w-0">
          <p className="text-body-phone font-semibold text-ink tabular-nums lining-nums lg:text-body" data-headline="">
            {counts}
          </p>
          <p className="mt-1 text-caption text-ink-secondary tabular-nums lining-nums">
            {copy.updated(clockWithSeconds(Date.parse(data.server_now)))}
          </p>
          <p role="status" className="sr-only" data-counts-announcement="">
            {said}
          </p>
        </div>
        <AutoUpdate controls={controls} />
      </div>
      <RailLayout
        rail={<OverviewRail data={data} groups={groups} now={now} />}
        after={
          groups.length > 0 ? (
            <>
              <h2 className="mt-12 text-headline text-ink">{copy.listTitle}</h2>
              {groups.map((group) => (
                <Group key={group.name} group={group} now={now} sessionId={sessionId} />
              ))}
            </>
          ) : undefined
        }
      >
        {groups.length === 0 ? (
          <p className="mt-8 text-body-phone text-ink lg:text-body">{copy.empty}</p>
        ) : (
          <OverviewWall
            sessionId={sessionId}
            groups={groups}
            now={now}
            heldAt={controls.heldAt?.receivedAt ?? null}
            returnTo={returnTo}
          />
        )}
      </RailLayout>
    </div>
  );
}

/** Back from Spillinnsikt (Story 7.7): the game named in `?spill=` and the view in `?visning=`,
 * read once, when the Oversikt opens; then the address drops them, so a reload or a later
 * re-render does not move focus again. */
function useReturnTo(sessionId: string): ReturnTo | null {
  const params = useSearchParams();
  const [found] = useState<ReturnTo | null>(() => {
    const id = params.get("spill");
    return id ? { id, view: params.get("visning") === "tabell" ? "table" : "wall" } : null;
  });
  useEffect(() => {
    if (found) window.history.replaceState(null, "", classOverviewPath(sessionId));
  }, [found, sessionId]);
  return found;
}

/** A game's name as the link to its Spillinnsikt (Story 7.7). A click that opens it elsewhere (a
 * new tab or window) leaves this page's address as it is. */
function GameLink({ sessionId, gameId, name }: { sessionId: string; gameId: string; name: string }) {
  return (
    <Link
      href={gameInsightPath(sessionId, gameId)}
      onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        rememberReturn(sessionId, gameId);
      }}
      standalone
      className="min-w-tap-target-min"
    >
      {name}
    </Link>
  );
}

/**
 * The wall beside the right rail from 1024 px, the rail under the wall below it (Story 7.6,
 * UX-DR40, EXPERIENCE.md → Responsive): in reading order the wall, the rail, then `after` (the game
 * list), which stands under the wall in the left column on a laptop.
 */
function RailLayout({ children, rail, after }: { children: React.ReactNode; rail: React.ReactNode; after?: React.ReactNode }) {
  return (
    // A container query in rem, not a media query: with text enlarged to 200 % the rail would
    // otherwise squeeze the wall into a few characters; it stands under the wall instead.
    <div className="@container">
      <div className="grid grid-cols-1 gap-x-10 @3xl:grid-cols-[minmax(0,1fr)_20rem] @5xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 @3xl:col-start-1 @3xl:row-start-1">{children}</div>
        <div className="mt-10 min-w-0 @3xl:col-start-2 @3xl:row-span-2 @3xl:row-start-1 @3xl:mt-8">{rail}</div>
        {after ? <div className="@container min-w-0 @3xl:col-start-1 @3xl:row-start-2">{after}</div> : null}
      </div>
    </div>
  );
}

/** The Bryter «Oppdater automatisk» with its state word, and while it is off and changes wait,
 * «3 endringer siden 14:02» with «Oppdater» (DESIGN.md → Oppdater automatisk, UX-DR44). */
function AutoUpdate({ controls }: { controls: LiveControls }) {
  const id = useId();
  const labelId = `${id}-label`;
  const held = controls.heldAt;
  return (
    <div className="flex flex-col items-start lg:items-end" data-auto-update="">
      <div className="flex flex-wrap items-center gap-x-3">
        <span id={labelId} className="text-label text-ink">
          {live.label}
        </span>
        <Switch id={`${id}-switch`} checked={controls.auto} labelledBy={labelId} onChange={controls.onAuto}>
          {controls.auto ? live.on : live.off}
        </Switch>
      </div>
      {held && controls.changes > 0 ? (
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-2 lg:justify-end">
          <p className="text-body-phone text-ink tabular-nums lining-nums lg:text-body">
            {live.changes(controls.changes, formatClock(Date.parse(held.overview.server_now)))}
          </p>
          <Button variant="secondary" onClick={controls.onApply}>
            {live.apply}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function Group({ group, now, sessionId }: { group: OverviewGroup; now: number; sessionId: string }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="mt-6 max-w-5xl">
      <h3 id={id} className="border-b border-axis pb-2 text-label text-ink tabular-nums lining-nums">
        {group.title} {group.games.length}
      </h3>
      <ul>
        {group.games.map((game) => (
          <GameRow key={game.game_id} game={game} now={now} sessionId={sessionId} />
        ))}
      </ul>
    </section>
  );
}

function GameRow({ game, now, sessionId }: { game: OverviewGame; now: number; sessionId: string }) {
  const name = copy.game(game.game_number ?? null);
  const cost = costText(game);
  const waits = waitLines(game, now);
  return (
    <li
      data-game={game.game_id}
      className="grid grid-cols-1 gap-y-1 border-b border-hairline py-3 @2xl:grid-cols-[7rem_5rem_minmax(0,1fr)_10rem] @2xl:gap-x-6"
    >
      <p className="text-label text-ink">
        <GameLink sessionId={sessionId} gameId={game.game_id} name={name} />
      </p>
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
      <p className="text-body-phone text-ink tabular-nums lining-nums @2xl:text-right lg:text-body">
        {cost ? (
          <>
            <span className="text-ink-secondary @2xl:sr-only">{copy.chainCost} </span>
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
function Allocation({ data, sessionId }: { data: ClassOverview; sessionId: string }) {
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
                <p className="text-label text-ink">
                  <GameLink sessionId={sessionId} gameId={game.game_id} name={name} />
                </p>
                <Seats game={game} label={copy.seatsLabel(name)} />
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
