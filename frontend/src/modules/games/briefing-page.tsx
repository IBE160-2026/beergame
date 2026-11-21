"use client";

import NextLink from "next/link";
import type { ReactNode } from "react";

import { buttonClassName } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { HOME_LINK, HOME_PATH, startingTaskPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { DEMO_GUIDED_ORDER, DEMO_SEAT } from "@/modules/landing/demo-seat";
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, useMyGame } from "./api";
import { capacityLines, delayLines, exampleCostLine, exampleRows, guidedLine, ratesLine } from "./briefing";
import { WeekTable } from "./week-table-view";

const copy = nb.games.briefing;

/**
 * «Regler før første ordre» (Story 6.2, FR-84, FR-14, UX-DR63, UX-DR70, mockup `09-alle-sider`):
 * the objective, how a Week goes, the game's own delays and Veiledede uker, how to play together,
 * and one Uke explained with the product's terms, labelled «Demodata»; a game that caps a Role adds
 * «Kapasitet» (Story 6.22, behind `FEATURE_CAPACITY` in the api). It never states the number
 * of Weeks and recommends no Order. Nothing is stored for reading it: Hjem leads here while the
 * api says `briefing_first`. The one primary button opens the Startoppgave (Story 6.3). Another
 * Student's game, or one not yet started, shows the permission-denied page (FR-5).
 */
export function BriefingPage({ gameId }: { gameId: string }) {
  return (
    <GuardedPage page="home">{(user, updatedAt) => <BriefingView gameId={gameId} user={user} updatedAt={updatedAt} />}</GuardedPage>
  );
}

function BriefingView({ gameId, user, updatedAt }: { gameId: string; user: SessionUser; updatedAt: number }) {
  const found = useMyGame(gameId);
  const { phase, retry } = usePageState(found, myGameKey(gameId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const game = found.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={game ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      <PageLink href={HOME_PATH.home}>{HOME_LINK.home}</PageLink>
      {game ? <Briefing game={game} /> : null}
    </PageShell>
  );
}

const BODY = "text-body-phone text-ink lg:text-body";

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="mt-8">
      <h2 id={id} className="text-headline text-ink">
        {title}
      </h2>
      <div className="mt-2 flex flex-col gap-2">{children}</div>
    </section>
  );
}

function Briefing({ game }: { game: MyGame }) {
  const { rules } = game;
  const capacity = capacityLines(game.role, rules);
  return (
    <div className="mt-4 max-w-prose">
      <p className={BODY}>{copy.lead(roleName(game.role), game.number)}</p>
      <Section id="briefing-goal" title={copy.goal.title}>
        <p className={BODY}>{copy.goal.text}</p>
        <p className={BODY}>{ratesLine(rules)}</p>
      </Section>
      <Section id="briefing-week" title={copy.week.title}>
        <p className={BODY}>{copy.week.same}</p>
        <p className={BODY}>{copy.week.ship}</p>
        <p className={BODY}>{copy.week.backlog}</p>
      </Section>
      {capacity.length > 0 ? (
        <Section id="briefing-capacity" title={copy.capacity.title}>
          {capacity.map((line) => (
            <p key={line} className={BODY}>
              {line}
            </p>
          ))}
        </Section>
      ) : null}
      <Section id="briefing-delays" title={copy.delays.title}>
        {delayLines(game.role, rules).map((line) => (
          <p key={line} className={BODY}>
            {line}
          </p>
        ))}
      </Section>
      <Section id="briefing-example" title={copy.example.title}>
        <GraphStrip />
        <WorkedWeek costLine={exampleCostLine(rules)} />
      </Section>
      <Section id="briefing-guided" title={copy.guided.title}>
        <p className={BODY}>{guidedLine(rules)}</p>
      </Section>
      <Section id="briefing-together" title={copy.together.title}>
        <p className={BODY}>{copy.together.continues}</p>
        <p className={BODY}>{copy.together.arrange}</p>
      </Section>
      <div className="mt-10">
        <NextLink href={startingTaskPath(game.id)} className={buttonClassName("primary")}>
          {copy.done}
        </NextLink>
      </div>
    </div>
  );
}

const STRIP_CAPTION = "briefing-strip-caption";

/** The graph strip (`09-alle-sider.png`): the Graf over tabell Students play on, over the Landing's
 * Demodata Seat, so the columns and the now-line are seen before the first Order. The caption
 * names the table, which is the graph's alternative. */
function GraphStrip() {
  return (
    <figure className="m-0 mb-6 max-w-full" aria-labelledby={STRIP_CAPTION}>
      <p id={STRIP_CAPTION} className={`mb-3 ${BODY}`}>
        {copy.example.strip}
      </p>
      <WeekTable state={DEMO_SEAT} nowOrder={DEMO_GUIDED_ORDER} labelledBy={STRIP_CAPTION} />
      <figcaption className="mt-2 text-right text-caption text-ink-muted">{copy.example.demoData}</figcaption>
    </figure>
  );
}

/** The worked Uke (Demodata): one column of a Grossist's week table, each number with what it
 * means, then the week's cost. */
function WorkedWeek({ costLine }: { costLine: string }) {
  const ex = copy.example;
  return (
    // At large text in a narrow column (200 % at 390 px) each row stacks: the term and its number
    // on one line, what it means under them, so «Hva det betyr» is never a few words a line. The
    // ARIA roles keep the table's reading when the rows are laid out as grids.
    <figure className="@container m-0">
      <table role="table" className="w-full border-collapse text-left text-table-cell leading-snug text-ink lg:text-table-cell-laptop">
        <caption className="mb-2 text-left text-label font-semibold text-ink">{ex.caption}</caption>
        <thead role="rowgroup" className="@max-[17rem]:sr-only">
          <tr role="row" className="border-b border-axis">
            <th role="columnheader" scope="col" className="py-2 pr-3 font-normal text-ink-secondary">
              {ex.term}
            </th>
            <th role="columnheader" scope="col" className="py-2 pr-3 text-right font-normal whitespace-nowrap text-ink-secondary">
              {ex.value}
            </th>
            <th role="columnheader" scope="col" className="py-2 font-normal text-ink-secondary">
              {ex.meaning}
            </th>
          </tr>
        </thead>
        <tbody role="rowgroup" className="@max-[17rem]:border-t @max-[17rem]:border-axis">
          {exampleRows().map((row) => (
            <tr
              key={row.key}
              role="row"
              className="border-b border-hairline align-top @max-[17rem]:grid @max-[17rem]:grid-cols-[minmax(0,1fr)_auto] @max-[17rem]:py-2"
            >
              <th role="rowheader" scope="row" className="py-2 pr-3 font-normal whitespace-nowrap @max-[17rem]:p-0">
                {row.term}
              </th>
              <td role="cell" className="py-2 pr-3 text-right font-normal tabular-nums lining-nums @max-[17rem]:p-0">
                {row.value}
              </td>
              <td role="cell" className="py-2 text-ink-secondary @max-[17rem]:col-span-2 @max-[17rem]:p-0 @max-[17rem]:pt-1">
                {row.meaning}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-body-phone text-ink lg:text-body">{costLine}</p>
      <figcaption className="mt-2 text-right text-caption text-ink-muted">{ex.demoData}</figcaption>
    </figure>
  );
}
