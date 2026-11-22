"use client";

import { useId } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import { AiNote, DebriefText } from "@/modules/debrief/ai-text";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { gamePath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { useWalkthrough, type Walkthrough, type WalkthroughMoment, walkthroughKey } from "./api";
import { ReplayClosed } from "./replay-closed";
import { unlikeReasons, walkthroughTotals, walkthroughView } from "./walkthrough";
import { CHART_LINES, WalkthroughChart } from "./walkthrough-chart";

const copy = nb.replay.walkthrough;
const LINE = "text-body-phone lg:text-body";
const LABEL = "text-label text-ink";

/**
 * Replay-gjennomgang (Story 10.7, FR-50, UX-DR64, EXPERIENCE.md → Replay-gjennomgang,
 * `09-alle-sider.png`): reached by «Gå til gjennomgangen» on «Replay er ferdig». The Student's
 * Totalkostnad, the Replay and their Class game on one Uke axis with «Vis som tabell», «Ikke like
 * for like.» with its reasons, the line that ties the moments together (marked «KI-generert, kan
 * ta feil:» only when `ai_generated`) and one or two moments of their own Replay Orders. While the
 * line is worded: «Gjennomgangen lages.» in a Skjelett of the chart, read again on `user:<id>` and
 * after the api's wait. A Class game played mostly by AI players is not set beside it, and the
 * page says why. A Replay closed at the Testfrist keeps Story 10.6's message; anyone else's
 * Replay shows the access-denied page. No ranking or praise (UX-DR72). Every number is the api's.
 */
export function WalkthroughPage({ gameId }: { gameId: string }) {
  return (
    <GuardedPage page="home">
      {(user, updatedAt) => <WalkthroughScreen gameId={gameId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function WalkthroughScreen({ gameId, user, updatedAt }: { gameId: string; user: SessionUser; updatedAt: number }) {
  const found = useWalkthrough(gameId);
  const { phase, retry } = usePageState(found, walkthroughKey(gameId));
  const code = found.error instanceof ApiRequestError ? found.error.code : null;
  const view = walkthroughView(found.data, code);
  if (view === "denied") return <AccessDenied user={user} updatedAt={updatedAt} />;
  if (view === "closed") {
    return (
      <PageShell user={user} title={nb.games.play.replayClosed.title} updatedAt={updatedAt}>
        <ReplayClosed />
      </PageShell>
    );
  }
  if (view === "notFinished") {
    return (
      <PageShell user={user} title={copy.title} updatedAt={updatedAt}>
        <p data-walkthrough-not-finished="" className={`${LINE} mt-4 max-w-md text-ink`}>
          {copy.notFinished}
        </p>
        <PageLink href={gamePath(gameId)}>{copy.toReplay}</PageLink>
      </PageShell>
    );
  }
  const data = found.data;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      {data ? (
        <>
          <p className={`${LINE} mt-1 text-ink-secondary`}>{copy.roleReplay(roleName(data.role))}</p>
          {view === "pending" ? <Pending /> : <Ready data={data} />}
        </>
      ) : null}
    </PageShell>
  );
}

/** «Gjennomgangen lages.» (UX-DR58, UX-DR64): a Skjelett where the chart will stand, the chart's
 * height, `hairline` rules and no numbers; the status line is announced politely. */
function Pending() {
  return (
    <div data-walkthrough-pending="" className="mt-6 max-w-3xl">
      <p role="status" className={`${LINE} text-ink`}>
        {copy.pending}
      </p>
      <div aria-hidden="true" data-skeleton="" className="mt-4 text-caption">
        <div className="h-3 w-48 max-w-full rounded-sm bg-hairline" />
        <div className="mt-3 flex flex-col justify-between border-b border-axis" style={{ height: `${CHART_LINES}em` }}>
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="border-t border-hairline" />
          ))}
        </div>
      </div>
    </div>
  );
}

function Ready({ data }: { data: Walkthrough }) {
  const id = useId();
  const totals = walkthroughTotals(data);
  return (
    <div data-walkthrough-ready="" className="max-w-3xl">
      <dl className="mt-6 flex flex-wrap gap-x-10 gap-y-4">
        <div>
          <dt className="text-label text-ink-secondary">{copy.totalLabel}</dt>
          <dd data-walkthrough-total="" className="mt-1 text-figure-hero leading-tight text-ink tabular-nums lining-nums">
            {totals.replay}
          </dd>
        </div>
        {totals.klass ? (
          <div>
            <dt className="text-label text-ink-secondary">{copy.classTotalLabel(data.class_game?.game_number ?? null)}</dt>
            <dd data-walkthrough-class-total="" className="mt-1 text-figure-hero leading-tight text-ink-secondary tabular-nums lining-nums">
              {totals.klass}
            </dd>
          </div>
        ) : null}
      </dl>
      <WalkthroughChart data={data} />
      {data.class_game ? (
        <section aria-labelledby={`${id}-unlike`} data-walkthrough-unlike="" className="mt-6">
          <h2 id={`${id}-unlike`} className={LABEL}>
            {copy.unlike}
          </h2>
          <ul className={`${LINE} mt-1 flex list-disc flex-col gap-1 pl-5 text-ink`}>
            {unlikeReasons(data).map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </section>
      ) : (
        <p data-walkthrough-mostly-ai="" className={`${LINE} mt-6 text-ink`}>
          {copy.mostlyAi}
        </p>
      )}
      <Moments data={data} />
    </div>
  );
}

function Moments({ data }: { data: Walkthrough }) {
  const id = useId();
  return (
    <section aria-labelledby={`${id}-moments`} data-walkthrough-moments="" className="mt-10 border-t border-axis pt-4">
      <h2 id={`${id}-moments`} className="text-headline text-ink">
        {copy.momentsTitle}
      </h2>
      {data.narration ? (
        <div role="group" aria-labelledby={`${id}-narration`} data-walkthrough-narration="" className="mt-3 text-caption text-ink-secondary">
          <h3 id={`${id}-narration`} className={LABEL}>
            {copy.narration}
          </h3>
          <p className="mt-1">
            <DebriefText text={data.narration} />
          </p>
          <AiNote text={data.narration} className="mt-1" />
        </div>
      ) : null}
      {data.moments.length === 0 ? (
        <p className={`${LINE} mt-4 text-ink`}>{copy.noMoments}</p>
      ) : (
        <ol className="mt-4 flex flex-col gap-8">
          {data.moments.map((moment) => (
            <MomentItem key={moment.id} moment={moment} />
          ))}
        </ol>
      )}
    </section>
  );
}

function MomentItem({ moment }: { moment: WalkthroughMoment }) {
  return (
    <li data-walkthrough-moment={moment.id} className={`${LINE} text-ink`}>
      <h3 className="text-body-lead text-ink">{moment.heading}</h3>
      <div className="mt-3 flex flex-col gap-3">
        <div>
          <h4 className={LABEL}>{copy.reckoned}</h4>
          <p className="mt-1">{moment.reckoning}</p>
        </div>
        <div>
          <h4 className={LABEL}>{copy.later}</h4>
          <p className="mt-1">{moment.later}</p>
        </div>
        <div>
          <h4 className={LABEL}>{copy.pattern}</h4>
          {moment.patterns.map((text, i) => (
            <p key={i} className="mt-1" data-walkthrough-pattern="">
              {text}
            </p>
          ))}
        </div>
      </div>
    </li>
  );
}
