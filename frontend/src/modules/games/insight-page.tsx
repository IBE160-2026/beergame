"use client";

import { useSearchParams } from "next/navigation";
import { useId } from "react";

import { Link } from "@/components/link";
import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import { cn } from "@/lib/utils";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import {
  classPath,
  classSessionPath,
  gameInsightPath,
  HOME_PATH,
  messagePath,
  overviewReturnPath,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type GameInsight, gameInsightKey, type InsightSeat, useGameInsight } from "./api";
import { InsightCharts } from "./insight-charts";
import { hasWeeks, holderText, linkTexts, roleTables, seatsUpstreamFirst, type WeekRow } from "./insight";

const copy = nb.insight;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Spillinnsikt (Story 7.7, charts from Story 7.8; FR-62, FR-34, UX-DR55): one Class game for the staff of its Class — its
 * number, status and four Seats upstream first, each Student Seat with its link slot, and per Role
 * (Detaljist to Fabrikk) a table of every opened Week in its own scrolling region: what came in,
 * inventory, backlog, the Order, the Week's cost, when the Week opened and the Order came and the time
 * between (Story 8.1, FR-35, Europe/Oslo), who played it and its marks in words. Every
 * number is the api's (AD-10). A new Week arrives on the game's `game:<id>` event (AD-8). Anyone
 * but the Class's staff sees the permission-denied page (FR-5).
 */
export function InsightPage({ sessionId, gameId }: { sessionId: string; gameId: string }) {
  const named = ID.test(sessionId) && ID.test(gameId);
  // The api's ids are lower case; the event stream names the game so.
  const [session, game] = [sessionId.toLowerCase(), gameId.toLowerCase()];
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <InsightView sessionId={session} gameId={game} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function InsightView({
  sessionId,
  gameId,
  user,
  updatedAt,
}: {
  sessionId: string;
  gameId: string;
  user: SessionUser;
  updatedAt: number;
}) {
  const found = useGameInsight(gameId);
  // Opened from «Vis som tabell»: the Oversikt crumb returns to the table.
  const from = useSearchParams().get("visning") === "tabell" ? "table" : "wall";
  const { phase, retry } = usePageState(found, gameInsightKey(gameId));
  const data = found.data;
  // A game of another Class session under this one's path is refused like any other.
  const elsewhere = data !== undefined && data.class_session_id !== sessionId;
  if ((found.error instanceof ApiRequestError && found.error.code === "forbidden") || elsewhere) {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const title = data ? copy.title(data.game_number ?? null) : undefined;
  const crumbs =
    data && title
      ? ([
          { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
          { label: data.class_name, href: classPath(data.class_id) },
          { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
          { label: nb.overview.crumb, href: overviewReturnPath(sessionId, gameId, from) },
          { label: copy.crumb(title), href: gameInsightPath(sessionId, gameId) },
        ] as const)
      : undefined;
  return (
    <PageShell
      user={user}
      title={title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 8, columns: 6 }}
      header={data && title ? <InsightHeader data={data} title={title} sessionId={sessionId} /> : undefined}
    >
      {data ? <InsightBody data={data} /> : null}
    </PageShell>
  );
}

function InsightHeader({ data, title, sessionId }: { data: GameInsight; title: string; sessionId: string }) {
  return (
    <header className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
      <h1 className="text-title-phone text-ink lg:text-title-page">{title}</h1>
      <p className="text-body-phone text-ink-secondary lg:text-body" data-status={data.status}>
        <span className="sr-only">{copy.statusLabel}: </span>
        {copy.status[data.status]}
      </p>
      {/* A Message to every Student of this Class game (Story 7.9). */}
      <Link
        href={messagePath(sessionId, { game: data.game_id })}
        aria-label={nb.messages.toGameLabel(data.game_number ?? null)}
        data-message-game=""
        standalone
      >
        {nb.messages.toGame}
      </Link>
    </header>
  );
}

export function InsightBody({ data }: { data: GameInsight }) {
  const seatsId = useId();
  const weeksId = useId();
  return (
    <div className="mt-6">
      <section aria-labelledby={seatsId}>
        <h2 id={seatsId} className="sr-only">
          {copy.seatsTitle}
        </h2>
        <ol
          aria-label={copy.seatsLabel}
          className="grid grid-cols-1 gap-x-8 gap-y-4 border-y border-axis py-4 sm:grid-cols-2 lg:grid-cols-4"
          data-insight-seats=""
        >
          {seatsUpstreamFirst(data).map((seat) => (
            <SeatItem key={seat.role} seat={seat} sessionId={data.class_session_id} gameId={data.game_id} />
          ))}
        </ol>
      </section>
      {!hasWeeks(data) ? (
        <p className="mt-8 text-body-phone text-ink lg:text-body">{copy.notStarted}</p>
      ) : (
        <>
          <InsightCharts data={data} />
          <section aria-labelledby={weeksId} className="mt-10">
            <h2 id={weeksId} className="text-headline text-ink">
              {copy.weeksTitle}
            </h2>
            {roleTables(data).map((table) => (
              <RoleTable key={table.role} name={table.name} rows={table.rows} />
            ))}
          </section>
        </>
      )}
    </div>
  );
}

function SeatItem({ seat, sessionId, gameId }: { seat: InsightSeat; sessionId: string; gameId: string }) {
  const links = linkTexts(seat);
  return (
    <li className="min-w-0" data-role={seat.role}>
      <p className="text-label text-ink">{roleName(seat.role)}</p>
      <p className="flex flex-wrap items-baseline gap-x-3 text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">
        <span>{holderText(seat)}</span>
        {/* A Message to the Student of this Seat (Story 7.9), titled with the game. */}
        {seat.holder === "student" && seat.user_id && seat.name ? (
          <Link
            href={messagePath(sessionId, { game: gameId, student: seat.user_id })}
            aria-label={nb.messages.toStudentLabel(seat.name)}
            data-message-student=""
            standalone
          >
            {nb.messages.toStudent}
          </Link>
        ) : null}
      </p>
      {typeof links === "string" ? (
        <p className="mt-1 text-caption text-ink-secondary" data-links="">
          {links}
        </p>
      ) : links ? (
        <ul className="mt-1 flex flex-wrap gap-x-4" data-links="">
          {links.map((link) => (
            <li key={`${link.kind}:${link.href}`}>
              <Link href={link.href} standalone>
                {link.text}
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

const CELL = "border-b border-hairline px-[0.6em] py-[0.35em] align-top";
const NUMBER = "text-right whitespace-nowrap";
const HEAD = "sticky top-0 z-20 bg-paper font-normal whitespace-nowrap text-ink-secondary";
const COLUMNS = copy.columns;

/**
 * One Role's Weeks, Week 1 first, one row each (NFR-6): Uke as the sticky row header and the
 * header row sticky while the region scrolls in both directions inside its height cap. Numbers at
 * `table-cell` size, right-aligned in even columns; who played and the marks in words.
 */
function RoleTable({ name, rows }: { name: string; rows: readonly WeekRow[] }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="mt-8" data-role-table="">
      <h3 id={id} className="text-label text-ink">
        {copy.region(name)}
      </h3>
      {/* `relative` makes the scrolled box hold the sr-only text of an Order not placed, so it
          never reaches past the page's edge. */}
      <ScrollRegion labelledBy={id} className="mt-2" scrollClassName="relative max-h-[min(28rem,70vh)] overflow-y-auto overscroll-contain">
        <table className="min-w-full border-separate border-spacing-0 text-table-cell text-ink tabular-nums lining-nums lg:text-table-cell-laptop">
          <caption className="sr-only">{copy.region(name)}</caption>
          <thead>
            <tr>
              <th scope="col" className={cn(CELL, HEAD, "left-0 z-30 text-left")}>
                {COLUMNS.week}
              </th>
              <th scope="col" className={cn(CELL, HEAD, "text-left")}>
                {COLUMNS.playedBy}
              </th>
              {[COLUMNS.incomingOrder, COLUMNS.incomingDelivery, COLUMNS.inventory, COLUMNS.backlog, COLUMNS.order, COLUMNS.cost].map(
                (header) => (
                  <th key={header} scope="col" className={cn(CELL, HEAD, "text-right")}>
                    {header}
                  </th>
                ),
              )}
              {[COLUMNS.opened, COLUMNS.ordered, COLUMNS.took].map((header) => (
                <th key={header} scope="col" className={cn(CELL, HEAD, "text-right")}>
                  {header}
                </th>
              ))}
              <th scope="col" className={cn(CELL, HEAD, "text-left")}>
                {COLUMNS.marks}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.week} data-week={row.week}>
                <th scope="row" className={cn(CELL, "sticky left-0 z-10 bg-paper text-left font-normal")}>
                  {row.week}
                </th>
                <td className={cn(CELL, "min-w-[8em] text-left")}>{row.playedBy}</td>
                <td className={cn(CELL, NUMBER)}>{row.incomingOrder}</td>
                <td className={cn(CELL, NUMBER)}>{row.incomingDelivery}</td>
                <td className={cn(CELL, NUMBER)}>{row.inventory}</td>
                <td className={cn(CELL, NUMBER)}>{row.backlog}</td>
                <td className={cn(CELL, NUMBER)}>
                  {row.order === "" ? <span className="sr-only">{copy.noOrder}</span> : row.order}
                </td>
                <td className={cn(CELL, NUMBER)}>{row.cost}</td>
                <td className={cn(CELL, NUMBER)} data-opened="">
                  {row.opened}
                </td>
                <td className={cn(CELL, NUMBER)} data-ordered="">
                  {row.ordered === "" ? <span className="sr-only">{copy.noOrder}</span> : row.ordered}
                </td>
                <td className={cn(CELL, NUMBER)} data-took="">
                  {row.took}
                </td>
                <td className={cn(CELL, "min-w-[12em] text-left")}>{row.marks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollRegion>
    </section>
  );
}
