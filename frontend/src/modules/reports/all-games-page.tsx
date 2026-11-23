"use client";

import { useRef } from "react";

import { MIN_WEEK_WIDTH, OrderLines } from "@/components/charts/order-lines";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useBoxSize } from "@/lib/box-size";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type ClassGames, classGamesKey, type RoleOrders, useClassGames } from "./all-games-api";
import { ownLine, rolesFabrikkFirst, sharedTop, tableColumns, tableRows } from "./all-games";
import { FALLBACK, REGION, SECONDARY, Section, Table, TEXT, Toggled } from "./class-report-parts";

const copy = nb.allGames;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * «Alle spill side om side» (Story 14.5, FR-86, NFR-6, UX-DR64, UX-DR72, UX-DR75): every Class
 * game's Orders per Uke for each Role, Fabrikk at the top, on one scale, the Student's own game
 * named in text and drawn thick with points; under each chart «Vis som tabell» in game-number
 * order. No names, no cost and no ranking: the api sends game numbers and Orders only (AD-14).
 * Until the Student's Debrief is done and the Play deadline has passed the api answers 403
 * `all_games_locked` and the page says what opens it; another session shows the permission-denied
 * page (FR-5). On a phone only the chart and the table scroll, each in its own region.
 */
export function AllGamesPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="home">
      {(user, updatedAt) =>
        ID.test(sessionId) ? (
          <AllGamesView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function AllGamesView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useClassGames(sessionId);
  const { phase, retry } = usePageState(found, classGamesKey(sessionId));
  const code = found.error instanceof ApiRequestError ? found.error.code : null;
  if (code === "forbidden") return <AccessDenied user={user} updatedAt={updatedAt} />;
  const locked = code === "all_games_locked";
  const data = found.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={data || locked ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {locked ? (
        <p className={`mt-4 max-w-2xl ${SECONDARY}`} data-all-games="locked">
          {copy.locked}
        </p>
      ) : null}
      {data ? <Games data={data} /> : null}
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
    </PageShell>
  );
}

function Games({ data }: { data: ClassGames }) {
  const games = data.roles[0]?.games.length ?? 0;
  if (games === 0 || data.weeks === 0) {
    return (
      <p className={`mt-4 max-w-2xl ${TEXT}`} data-all-games="none">
        {copy.none}
      </p>
    );
  }
  const top = sharedTop(data);
  return (
    <div className="mt-4 flex max-w-4xl min-w-0 flex-col gap-8" data-all-games="open">
      <div className="flex flex-col gap-1">
        <p className={SECONDARY}>{copy.intro}</p>
        <p className={`${TEXT} font-semibold`} data-own-line="">
          {ownLine(data)}
        </p>
        <p className={SECONDARY}>{copy.axis}</p>
      </div>
      {rolesFabrikkFirst(data).map((role) => (
        <RoleSection key={role.role} role={role} weeks={data.weeks} top={top} />
      ))}
    </div>
  );
}

function RoleSection({ role, weeks, top }: { role: RoleOrders; weeks: number; top: number }) {
  const name = roleName(role.role);
  return (
    <Section title={name} name={role.role}>
      <Toggled
        name={role.role}
        chart={<Chart role={role} weeks={weeks} top={top} />}
        table={
          <Table
            caption={copy.tableCaption(name)}
            columns={tableColumns(weeks)}
            rows={tableRows(role)}
            name={role.role}
          />
        }
      />
    </Section>
  );
}

/** The chart in its own scroll region: as wide as its box, or wider when the Uker would be too
 * narrow (a phone), so only the chart scrolls, never the page (UX-DR75). */
function Chart({ role, weeks, top }: { role: RoleOrders; weeks: number; top: number }) {
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const title = copy.chartTitle(roleName(role.role), role.games.length);
  const width = Math.max(size.width, Math.ceil(weeks * MIN_WEEK_WIDTH + size.fontSize * 4));
  const height = Math.round(size.fontSize * 11);
  return (
    <div ref={box} className="min-w-0 text-caption" data-order-lines={role.role}>
      <div role="region" aria-label={title} tabIndex={0} className={REGION}>
        <OrderLines
          width={width}
          height={height}
          fontSize={size.fontSize}
          top={top}
          lines={role.games.map((game) => ({ key: String(game.number), own: game.own, orders: game.orders }))}
          title={title}
          formatTick={(value) => formatNumber(value, { decimals: 0 })}
          firstLabel={copy.week(1)}
          lastLabel={copy.week(Math.max(1, weeks))}
        />
      </div>
    </div>
  );
}
