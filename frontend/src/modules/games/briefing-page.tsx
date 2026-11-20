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
import { roleName } from "@/modules/sessions/sessions";

import { type MyGame, myGameKey, useMyGame } from "./api";
import { delayLines, exampleCostLine, exampleRows, guidedLine, ratesLine } from "./briefing";

const copy = nb.games.briefing;

/**
 * «Regler før første ordre» (Story 6.2, FR-84, FR-14, UX-DR63, UX-DR70, mockup `09-alle-sider`):
 * the objective, how a Week goes, the game's own delays and Veiledede uker, how to play together,
 * and one Uke explained with the product's terms, labelled «Demodata». It never states the number
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
      <Section id="briefing-delays" title={copy.delays.title}>
        {delayLines(game.role, rules).map((line) => (
          <p key={line} className={BODY}>
            {line}
          </p>
        ))}
      </Section>
      <Section id="briefing-example" title={copy.example.title}>
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

/** The worked Uke (Demodata): one column of a Grossist's week table, each number with what it
 * means, then the week's cost. */
function WorkedWeek({ costLine }: { costLine: string }) {
  const ex = copy.example;
  return (
    <figure className="m-0">
      <table className="w-full border-collapse text-left text-table-cell leading-snug text-ink lg:text-table-cell-laptop">
        <caption className="mb-2 text-left text-label font-semibold text-ink">{ex.caption}</caption>
        <thead>
          <tr className="border-b border-axis">
            <th scope="col" className="py-2 pr-3 font-normal text-ink-secondary">
              {ex.term}
            </th>
            <th scope="col" className="py-2 pr-3 text-right font-normal whitespace-nowrap text-ink-secondary">
              {ex.value}
            </th>
            <th scope="col" className="py-2 font-normal text-ink-secondary">
              {ex.meaning}
            </th>
          </tr>
        </thead>
        <tbody>
          {exampleRows().map((row) => (
            <tr key={row.key} className="border-b border-hairline align-top">
              <th scope="row" className="py-2 pr-3 font-normal whitespace-nowrap">
                {row.term}
              </th>
              <td className="py-2 pr-3 text-right font-bold tabular-nums lining-nums">{row.value}</td>
              <td className="py-2 text-ink-secondary">{row.meaning}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-body-phone text-ink lg:text-body">{costLine}</p>
      <figcaption className="mt-2 text-right text-caption text-ink-muted">{ex.demoData}</figcaption>
    </figure>
  );
}
