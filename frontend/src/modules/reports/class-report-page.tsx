"use client";

import { useId } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import { funnelRows } from "@/modules/games/overview";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classOverviewPath, classPath, classReportPath, classSessionPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { type ClassReport, classReportKey, useClassReport } from "./class-report-api";
import {
  aiSeatsLine,
  amplificationRows,
  costRoleRows,
  costSummary,
  coveredLine,
  fabrikkFirst,
  guardLine,
  hundredth,
  llmRows,
  modeName,
  patternBars,
  ratingBars,
  ratingLine,
  sharedHighest,
  statusLine,
  switchLines,
  whole,
} from "./class-report";
import { LearningPart } from "./class-report-learning-part";
import { Bars, Distribution, SECONDARY, Section, Table, TEXT, Toggled } from "./class-report-parts";

const copy = nb.classReport;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Klasserapport (Story 14.1, FR-64, FR-68, FR-70, FR-79, UX-DR55): how the Class games of a
 * Class session went, for the Lecturers of the Class; anyone else sees the permission-denied page
 * (FR-5). Every number is the api's (AD-10): the page formats and orders, never computes. Each
 * chart has «Vis som tabell» under it. A finished game or a recorded step emits `session:<id>`,
 * which refetches the report (`topics.ts`, AD-8).
 */
export function ClassReportPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        ID.test(sessionId) ? (
          <ReportView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function ReportView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useClassReport(sessionId);
  const { phase, retry } = usePageState(found, classReportKey(sessionId));
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
        { label: copy.crumb, href: classReportPath(sessionId) },
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
      skeleton={{ rows: 6, columns: 2 }}
    >
      {data ? <Report data={data} sessionId={sessionId} /> : null}
    </PageShell>
  );
}

function Report({ data, sessionId }: { data: ClassReport; sessionId: string }) {
  const covered = coveredLine(data);
  return (
    <div className="mt-2 flex min-w-0 flex-col" data-class-report="">
      <p className={`${SECONDARY} [overflow-wrap:anywhere]`}>{copy.session(data.session_number, data.class_name)}</p>
      <p className={`mt-2 ${TEXT} font-semibold`} data-report-status="">
        {statusLine(data)}
      </p>
      <div className="mt-8 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
        <Funnel data={data} />
        {data.cost ? <ChainCost cost={data.cost} /> : null}
        {data.cost ? <RoleCost cost={data.cost} /> : null}
        {data.finished > 0 ? <Amplification data={data} covered={covered} /> : null}
        {data.finished > 0 ? <Patterns data={data} covered={covered} /> : null}
        {data.finished > 0 ? <AiPlayers ai={data.ai} /> : null}
        {data.finished > 0 ? <Ratings ratings={data.ratings} /> : null}
      </div>
      <LearningPart sessionId={sessionId} />
    </div>
  );
}

function Funnel({ data }: { data: ClassReport }) {
  const rows = funnelRows(data.funnel);
  return (
    <Section title={copy.funnel.title} name="funnel">
      <Toggled
        name="funnel"
        chart={
          <Bars
            name="funnel"
            colour="border-order-history"
            rows={rows.map((row) => ({
              key: row.stage,
              label: row.label,
              count: whole(row.count),
              share: row.share,
              reads: `${row.label}: ${whole(row.count)}`,
            }))}
          />
        }
        table={
          <Table
            name="funnel"
            caption={copy.funnel.tableCaption}
            columns={[copy.funnel.stageColumn, copy.funnel.countColumn]}
            rows={rows.map((row) => ({ key: row.stage, head: row.label, cells: [whole(row.count)] }))}
          />
        }
      />
    </Section>
  );
}

function ChainCost({ cost }: { cost: NonNullable<ClassReport["cost"]> }) {
  const games = cost.games.length;
  return (
    <Section title={copy.chain.title} name="chain" intro={copy.chain.intro(games)}>
      <Toggled
        name="chain"
        chart={
          <>
            <Distribution
              name="chain"
              spread={cost.chain}
              title={copy.chain.chartTitle(games)}
              medianLabel={copy.median(whole(cost.chain.median))}
              formatTick={(value) => whole(value)}
            />
            <p className="mt-1 text-caption text-ink-secondary">{copy.chain.axis}</p>
          </>
        }
        table={
          <Table
            name="chain"
            caption={copy.chain.tableCaption}
            columns={[copy.gameColumn, copy.chain.costColumn]}
            rows={cost.games.map((game, i) => ({
              key: String(game.number ?? i),
              head: nb.overview.game(game.number ?? null),
              cells: [whole(game.chain_cost)],
            }))}
          />
        }
      />
      <p className={`mt-2 ${TEXT} tabular-nums lining-nums`} data-chain-summary="">
        {costSummary(cost.chain)}
      </p>
      <p className={`mt-1 ${TEXT} tabular-nums lining-nums`} data-chain-split="">
        {copy.chain.split(whole(cost.holding_cost), whole(cost.backorder_cost))}
      </p>
    </Section>
  );
}

function RoleCost({ cost }: { cost: NonNullable<ClassReport["cost"]> }) {
  const highest = sharedHighest(cost.roles.map((role) => role.distribution));
  return (
    <Section title={copy.roles.title} name="roles" intro={copy.roles.intro}>
      <Toggled
        name="roles"
        chart={
          <ul data-role-costs="">
            {fabrikkFirst(cost.roles).map((role) => {
              const name = roleName(role.role);
              return (
                <li key={role.role} className="mt-3 first:mt-1" data-role={role.role}>
                  <h3 className="text-label text-ink">{name}</h3>
                  <Distribution
                    name={`cost-${role.role}`}
                    spread={role.distribution}
                    title={copy.roles.chartTitle(name)}
                    medianLabel={copy.median(whole(role.distribution.median))}
                    formatTick={(value) => whole(value)}
                    highest={highest}
                  />
                  <p className={`${TEXT} tabular-nums lining-nums`} data-role-line="">
                    {copy.roles.line(whole(role.distribution.median), whole(role.holding_cost), whole(role.backorder_cost))}
                  </p>
                </li>
              );
            })}
          </ul>
        }
        table={
          <Table
            name="roles"
            caption={copy.roles.tableCaption}
            columns={[copy.roleColumn, copy.medianColumn, copy.middleColumn, copy.roles.holdingColumn, copy.roles.backorderColumn]}
            rows={costRoleRows(cost).map((row) => ({
              key: row.role,
              head: row.name,
              cells: [row.median, row.middle, row.holding, row.backorder],
            }))}
          />
        }
      />
    </Section>
  );
}

function Amplification({ data, covered }: { data: ClassReport; covered: string | null }) {
  const shown = data.amplification.filter((row) => row.distribution);
  const highest = sharedHighest(data.amplification.map((row) => row.distribution));
  const value = (text: string) => copy.amplification.value(text);
  return (
    <Section title={copy.amplification.title} name="amplification" intro={copy.amplification.intro}>
      {covered ? <p className={`mt-1 ${SECONDARY}`} data-covered="">{covered}</p> : null}
      {data.facts_games === 0 ? (
        <p className={`mt-2 ${TEXT}`}>{copy.amplification.none}</p>
      ) : shown.length === 0 ? (
        <p className={`mt-2 ${TEXT}`}>{copy.amplification.noValue}</p>
      ) : (
        <Toggled
          name="amplification"
          chart={
            <ul>
              {fabrikkFirst(data.amplification).map((row) => {
                const name = roleName(row.role);
                return (
                  <li key={row.role} className="mt-3 first:mt-1" data-role={row.role}>
                    <h3 className="text-label text-ink">{name}</h3>
                    {row.distribution ? (
                      <>
                        <Distribution
                          name={`amplification-${row.role}`}
                          spread={row.distribution}
                          title={copy.amplification.chartTitle(name)}
                          medianLabel={copy.median(value(hundredth(row.distribution.median)))}
                          formatTick={(tick) => hundredth(tick).replace(/,00$/, "")}
                          highest={highest}
                        />
                        <p className={`${TEXT} tabular-nums lining-nums`} data-role-line="">
                          {copy.summary(
                            value(hundredth(row.distribution.median)),
                            hundredth(row.distribution.lower_quartile),
                            hundredth(row.distribution.upper_quartile),
                          )}
                        </p>
                      </>
                    ) : (
                      <p className={SECONDARY}>{copy.amplification.noValue}</p>
                    )}
                  </li>
                );
              })}
            </ul>
          }
          table={
            <Table
              name="amplification"
              caption={copy.amplification.tableCaption}
              columns={[copy.roleColumn, copy.amplification.gamesColumn, copy.medianColumn, copy.middleColumn]}
              rows={amplificationRows(data.amplification).map((row) => ({
                key: row.role,
                head: row.name,
                cells: [whole(row.games), row.median ?? "–", row.middle ?? "–"],
              }))}
            />
          }
        />
      )}
    </Section>
  );
}

function Patterns({ data, covered }: { data: ClassReport; covered: string | null }) {
  const bars = patternBars(data.patterns);
  return (
    <Section title={copy.patterns.title} name="patterns" intro={copy.patterns.intro}>
      {covered ? <p className={`mt-1 ${SECONDARY}`}>{covered}</p> : null}
      {data.facts_games === 0 ? (
        <p className={`mt-2 ${TEXT}`}>{copy.amplification.none}</p>
      ) : bars.length === 0 ? (
        <p className={`mt-2 ${TEXT}`}>{copy.patterns.none}</p>
      ) : (
        <Toggled
          name="patterns"
          chart={
            <Bars
              name="patterns"
              colour="border-restordre"
              rows={bars.map((bar) => ({ key: bar.pattern, label: bar.name, count: bar.count, share: bar.share, reads: bar.reads }))}
            />
          }
          table={
            <Table
              name="patterns"
              caption={copy.patterns.tableCaption}
              columns={[copy.patterns.patternColumn, copy.patterns.occurrencesColumn, copy.patterns.gamesColumn]}
              rows={bars.map((bar) => ({ key: bar.pattern, head: bar.name, cells: [bar.count, bar.games] }))}
            />
          }
        />
      )}
    </Section>
  );
}

function AiPlayers({ ai }: { ai: ClassReport["ai"] }) {
  const switches = switchLines(ai);
  const switchesId = useId();
  const llmId = useId();
  return (
    <Section title={copy.ai.title} name="ai">
      <p className={`mt-2 ${TEXT} tabular-nums lining-nums`} data-ai-seats="">
        {aiSeatsLine(ai)}
      </p>
      <p className={`mt-1 ${TEXT} tabular-nums lining-nums`} data-guard="">
        {guardLine(ai)}
      </p>
      <h3 id={switchesId} className="mt-4 text-label text-ink">
        {copy.ai.switchesTitle}
      </h3>
      {switches.length === 0 ? (
        <p className={`mt-1 ${SECONDARY}`}>{copy.ai.noSwitches}</p>
      ) : (
        <ul aria-labelledby={switchesId} className="mt-1" data-switches="">
          {switches.map((line) => (
            <li key={line} className={`${TEXT} py-0.5 tabular-nums lining-nums [overflow-wrap:anywhere]`}>
              {line}
            </li>
          ))}
        </ul>
      )}
      <h3 id={llmId} className="mt-4 text-label text-ink">
        {copy.ai.llmTitle}
      </h3>
      <p className="mt-1 text-caption text-ink-secondary">{copy.ai.llmIntro}</p>
      <Table
        name="llm"
        caption={copy.ai.tableCaption}
        columns={[copy.gameColumn, copy.ai.orderedColumn, copy.ai.llmColumn, copy.ai.shareColumn, copy.ai.fallbackColumn]}
        rows={llmRows(ai).map((row) => ({ key: row.game, head: row.game, cells: [row.ordered, row.llm, row.share, row.fallback] }))}
      />
    </Section>
  );
}

function Ratings({ ratings }: { ratings: ClassReport["ratings"] }) {
  return (
    <Section title={copy.ratings.title} name="ratings" intro={copy.ratings.intro}>
      {ratings.length === 0 ? (
        <p className={`mt-2 ${TEXT}`}>{copy.ratings.none}</p>
      ) : (
        ratings.map((mode) => (
          <div key={mode.ai_mode} className="mt-3" data-rating-mode={mode.ai_mode}>
            <p className={`${TEXT} font-semibold tabular-nums lining-nums`}>{ratingLine(mode)}</p>
            <Toggled
              name={`ratings-${mode.ai_mode}`}
              chart={
                <Bars
                  name={`ratings-${mode.ai_mode}`}
                  colour="border-lager"
                  rows={ratingBars(mode).map((bar) => ({
                    key: String(bar.rating),
                    label: String(bar.rating),
                    count: whole(bar.count),
                    share: bar.share,
                    reads: bar.reads,
                  }))}
                />
              }
              table={
                <Table
                  name={`ratings-${mode.ai_mode}`}
                  caption={copy.ratings.tableCaption(modeName(mode.ai_mode))}
                  columns={[copy.ratings.ratingColumn, copy.ratings.countColumn]}
                  rows={mode.values.map((v) => ({ key: String(v.rating), head: String(v.rating), cells: [whole(v.count)] }))}
                />
              }
            />
          </div>
        ))
      )}
    </Section>
  );
}
