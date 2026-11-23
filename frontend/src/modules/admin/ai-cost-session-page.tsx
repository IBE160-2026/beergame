"use client";

import { type FormEvent, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import { cn } from "@/lib/utils";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_AI_COSTS_PATH, adminAiCostPath } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { Bar, ChartBlock, TableRegion } from "@/modules/ops/ops-charts";

import { costPercent, costText, gameName, parseLimit } from "./ai-cost";
import { COST_CRUMBS, TargetFigure, TEXT } from "./ai-cost-page";
import { refusalText } from "./ai-models";
import { type SessionCost, sessionCostKey, useSessionCost, useSetCostLimit, useStopAssessment } from "./api";
import { formatTime } from "./audit";
import { dayText } from "./daily-spend";

const copy = nb.admin.aiCost.cost;
const NOTICE = "border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body";
const HEAD = "border-b border-axis py-2 pr-4 align-bottom text-label font-semibold text-ink";
const CELL = "border-b border-hairline py-1.5 pr-4";
const COST_FILL = "var(--color-lager)";

/**
 * One Class session's AI cost and its limit (Story 15.6, FR-69, FR-44, UX-DR57): the limit,
 * reserve and spent of its budget row; the limit-reached line with its time; when the reserve is
 * used up too, what that means and the two actions, each with its consequence above its button
 * (raise the limit, which restarts the AI assessment; stop the AI assessment); the cost per Game
 * and per day as charts with «Vis som tabell». The limit save is the page's one primary button.
 */
export function AiCostSessionPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => <Shell user={user} updatedAt={updatedAt} sessionId={sessionId} />}
    </GuardedPage>
  );
}

/** Inside the guard, so only an Admin's page asks for the cost at all. */
function Shell({
  user,
  updatedAt,
  sessionId,
}: {
  user: Parameters<typeof PageShell>[0]["user"];
  updatedAt: Parameters<typeof PageShell>[0]["updatedAt"];
  sessionId: string;
}) {
  const cost = useSessionCost(sessionId);
  const title = cost.data?.label ?? nb.admin.aiCost.costs.title;
  return (
    <PageShell
      user={user}
      title={title}
      updatedAt={updatedAt}
      crumbs={[...COST_CRUMBS, { label: title, href: adminAiCostPath(sessionId) }]}
    >
      <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
      <Content sessionId={sessionId} />
    </PageShell>
  );
}

function Content({ sessionId }: { sessionId: string }) {
  const cost = useSessionCost(sessionId);
  const pageState = usePageState(cost, sessionCostKey(sessionId));
  if (pageState.phase === "loading" || pageState.phase === "slow") {
    return (
      <div className="mt-10">
        <Skeleton heading={false} rows={4} columns={3} />
        <LoadingNote visible={pageState.phase === "slow"} />
      </div>
    );
  }
  // An unknown Class session, or a path that names none (422): the same «finnes ikke».
  if (cost.error instanceof ApiRequestError && [404, 422].includes(cost.error.status)) {
    return (
      <div className="mt-10 flex flex-col items-start gap-3">
        <p className={TEXT}>{copy.notFound}</p>
        <Link href={ADMIN_AI_COSTS_PATH} standalone>
          {nb.admin.aiCost.costs.back}
        </Link>
      </div>
    );
  }
  if (pageState.phase === "failed" || !cost.data) {
    return (
      <div className="mt-10 flex flex-col items-start gap-3">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button onClick={pageState.retry}>{nb.system.retry}</Button>
      </div>
    );
  }
  return <SessionCostView found={cost.data} />;
}

export function SessionCostView({ found }: { found: SessionCost }) {
  return (
    <>
      <State found={found} />
      <BudgetSection found={found} />
      <GamesChart found={found} />
      <DaysChart found={found} />
    </>
  );
}

/** The cost-limit state: reached (with its time), the reserve used up, the assessment stopped. */
function State({ found }: { found: SessionCost }) {
  const reachedAt = found.budget?.players_exhausted_at;
  if (!reachedAt && !found.assessment_stopped_at) return null;
  return (
    <div className={cn(NOTICE, "mt-8 flex max-w-2xl flex-col gap-1")} data-cost-state="">
      {reachedAt ? (
        <p className="font-semibold">
          {copy.reached(found.label)} {copy.reachedAt(formatTime(reachedAt))}
        </p>
      ) : null}
      {found.reserve_used_up ? <p>{copy.reserveUsed}</p> : null}
      {found.assessment_stopped_at ? <p>{copy.stoppedAt(formatTime(found.assessment_stopped_at))}</p> : null}
    </div>
  );
}

function BudgetSection({ found }: { found: SessionCost }) {
  const text = copy.budget;
  const budget = found.budget;
  const rows: [string, string][] = budget
    ? [
        [text.limit, costText(budget.limit_usd)],
        [text.reserve, costText(budget.reserve_usd)],
        [text.spent, costText(budget.spent_usd)],
        [text.held, costText(budget.reserved_usd)],
      ]
    : [];
  return (
    <section aria-labelledby="budget-title" className="mt-10">
      <h2 id="budget-title" className="text-headline text-ink">
        {text.title}
      </h2>
      <p className={cn(TEXT, "mt-2 tabular-nums lining-nums")}>
        {text.total(costText(found.total_usd), formatNumber(found.calls))}
      </p>
      <p className={cn(TEXT, "tabular-nums lining-nums")}>
        {nb.admin.aiCost.costs.columns.perGame}: <TargetFigure amount={found.per_game_usd} above={found.per_game_above} />
        {" · "}
        {nb.admin.aiCost.costs.columns.perStudent}:{" "}
        <TargetFigure amount={found.per_student_usd} above={found.per_student_above} />
      </p>
      {budget ? (
        <dl className="mt-4 grid max-w-md grid-cols-[1fr_auto] gap-x-6 gap-y-1 text-body-phone tabular-nums lining-nums lg:text-body">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-ink-secondary">{label}</dt>
              <dd className="text-right text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className={cn(TEXT, "mt-4")}>{text.none}</p>
      )}
      <LimitForm found={found} />
      {found.can_stop ? <StopAction found={found} /> : null}
    </section>
  );
}

function LimitForm({ found }: { found: SessionCost }) {
  const save = useSetCostLimit(found.class_session_id);
  const [value, setValue] = useState(found.budget ? formatNumber(found.budget.limit_usd, { narrow: true }) : "");
  const [invalid, setInvalid] = useState(false);
  const [saved, setSaved] = useState<string>();
  const waiting = found.reserve_used_up || found.assessment_stopped_at !== null;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (save.isPending) return;
    save.reset();
    setSaved(undefined);
    const limit = parseLimit(value);
    setInvalid(limit === null);
    if (limit === null) return;
    save.mutate(limit, {
      onSuccess: (next) => setSaved(next.budget ? copy.saved(costText(next.budget.limit_usd)) : undefined),
    });
  }

  return (
    <form method="post" noValidate onSubmit={onSubmit} className="mt-8 flex max-w-md flex-col gap-4">
      {waiting ? <p className={TEXT}>{copy.raiseConsequence}</p> : null}
      <TextField
        id="cost-limit"
        label={copy.limitLabel}
        hint={copy.limitHint}
        inputMode="decimal"
        autoComplete="off"
        value={value}
        error={invalid ? copy.invalid : undefined}
        onChange={(event) => {
          setInvalid(false);
          setValue(event.target.value);
        }}
      />
      <ActionError message={save.isError ? refusalText(save.error, copy.refused, copy.failed) : undefined} />
      <Button type="submit" variant="primary" unavailable={save.isPending} className="w-full sm:w-auto sm:self-start">
        {copy.save}
      </Button>
      <p aria-live="polite" className={TEXT}>
        {saved ?? ""}
      </p>
    </form>
  );
}

function StopAction({ found }: { found: SessionCost }) {
  const stop = useStopAssessment(found.class_session_id);
  return (
    <div className="mt-8 flex max-w-md flex-col gap-4" data-stop-assessment="">
      <p className={TEXT}>{copy.stopConsequence}</p>
      <ActionError message={stop.isError ? refusalText(stop.error, copy.refused, copy.failed) : undefined} />
      <Button
        unavailable={stop.isPending}
        className="w-full sm:w-auto sm:self-start"
        onClick={() => {
          if (!stop.isPending) stop.mutate();
        }}
      >
        {copy.stop}
      </Button>
    </div>
  );
}

/** One bar per line, on one scale (the largest line), with its amount and calls beside it. */
function CostBars({ lines, kind }: { lines: { key: string; name: string; usd: string; above?: boolean }[]; kind: string }) {
  const top = Math.max(0, ...lines.map((line) => Number(line.usd)));
  return (
    <ul className="flex max-w-2xl flex-col gap-3" data-chart={kind}>
      {lines.map((line) => (
        <li key={line.key} className="grid grid-cols-1 gap-1 sm:grid-cols-[10em_1fr_12em] sm:items-center sm:gap-4">
          <span className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">{line.name}</span>
          <Bar parts={[{ width: costPercent(line.usd, top), colour: COST_FILL }]} />
          <span className="text-body-phone text-ink tabular-nums lining-nums lg:text-body">
            {costText(line.usd)}
            {line.above ? ` · ${nb.admin.aiCost.costs.above}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}

function GamesChart({ found }: { found: SessionCost }) {
  const text = copy.games;
  const lines = found.per_game.map((line) => ({
    key: line.game_id ?? "none",
    name: gameName(line),
    usd: line.usd,
    above: line.above,
    calls: line.calls,
  }));
  if (lines.length === 0) {
    return (
      <section aria-labelledby="games-title" className="mt-10">
        <h2 id="games-title" className="text-headline text-ink">
          {text.title}
        </h2>
        <p className={cn(TEXT, "mt-2")}>{text.empty}</p>
      </section>
    );
  }
  return (
    <ChartBlock
      kind="cost-games"
      title={text.title}
      lead={text.lead}
      chart={<CostBars lines={lines} kind="cost-games" />}
      table={
        <TableRegion caption={text.table}>
          <thead>
            <tr>
              <th scope="col" className={HEAD}>
                {text.columns.game}
              </th>
              <th scope="col" className={cn(HEAD, "text-right")}>
                {text.columns.cost}
              </th>
              <th scope="col" className={cn(HEAD, "text-right")}>
                {text.columns.calls}
              </th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.key}>
                <th scope="row" className={cn(CELL, "font-normal")}>
                  {line.name}
                </th>
                <td className={cn(CELL, "text-right")}>
                  {costText(line.usd)}
                  {line.above ? ` · ${nb.admin.aiCost.costs.above}` : ""}
                </td>
                <td className={cn(CELL, "text-right")}>{formatNumber(line.calls)}</td>
              </tr>
            ))}
          </tbody>
        </TableRegion>
      }
    />
  );
}

function DaysChart({ found }: { found: SessionCost }) {
  const text = copy.days;
  const lines = found.per_day.map((line) => ({
    key: line.day,
    name: dayText(line.day),
    usd: line.usd,
    calls: line.calls,
  }));
  if (lines.length === 0) {
    return (
      <section aria-labelledby="days-title" className="mt-10">
        <h2 id="days-title" className="text-headline text-ink">
          {text.title}
        </h2>
        <p className={cn(TEXT, "mt-2")}>{text.empty}</p>
      </section>
    );
  }
  return (
    <ChartBlock
      kind="cost-days"
      title={text.title}
      lead={text.lead}
      chart={<CostBars lines={lines} kind="cost-days" />}
      table={
        <TableRegion caption={text.table}>
          <thead>
            <tr>
              <th scope="col" className={HEAD}>
                {text.columns.day}
              </th>
              <th scope="col" className={cn(HEAD, "text-right")}>
                {text.columns.cost}
              </th>
              <th scope="col" className={cn(HEAD, "text-right")}>
                {text.columns.calls}
              </th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.key}>
                <th scope="row" className={cn(CELL, "font-normal")}>
                  {line.name}
                </th>
                <td className={cn(CELL, "text-right")}>{costText(line.usd)}</td>
                <td className={cn(CELL, "text-right")}>{formatNumber(line.calls)}</td>
              </tr>
            ))}
          </tbody>
        </TableRegion>
      }
    />
  );
}
