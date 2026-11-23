"use client";

import { type ReactNode } from "react";

import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { LoadingNote, Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import { GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_AI_COST_PATH, ADMIN_AI_COSTS_PATH, adminAiCostPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { costText } from "./ai-cost";
import { type CostList, type SessionCostItem, sessionCostsKey, useSessionCosts } from "./api";
import { Cell } from "./user-list";

const copy = nb.admin.aiCost.costs;

export const COST_CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: nb.admin.aiCost.title, href: ADMIN_AI_COST_PATH },
  { label: copy.title, href: ADMIN_AI_COSTS_PATH },
] as const;

export const TABLE =
  "w-full border-collapse text-left text-table-cell tabular-nums lining-nums text-ink @max-[60em]:block lg:text-table-cell-laptop";
export const HEAD = "py-2 pr-6 align-bottom text-label font-semibold text-ink";
export const ROW = "border-b border-hairline align-baseline @max-[60em]:block @max-[60em]:py-3";
export const BODY = "@max-[60em]:block @max-[60em]:border-t @max-[60em]:border-axis";
export const TEXT = "text-body-phone text-ink lg:text-body";
const LEAD = "mt-2 mb-5 max-w-2xl text-body-phone text-ink-secondary lg:text-body";

/** A figure's cell: right-aligned in the table, labelled and left-aligned once the row is a block. */
export function NumberCell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <td className="py-3 pr-6 @min-[60em]:text-right @min-[60em]:whitespace-nowrap @max-[60em]:flex @max-[60em]:gap-3 @max-[60em]:py-1 @max-[60em]:pr-0">
      <span className="w-24 shrink-0 text-ink-secondary @min-[60em]:hidden">{label}</span>
      <span className="min-w-0 @max-[60em]:[overflow-wrap:anywhere]">{children}</span>
    </td>
  );
}

/** A per-Game or per-Student figure with the text mark «Over målet» when it is above its target
 * (C-3): text, never colour alone. */
export function TargetFigure({ amount, above }: { amount: string | null; above: boolean }) {
  if (amount === null) return <>{copy.none}</>;
  return (
    <>
      {costText(amount)}
      {above ? <span className="block font-semibold text-ink @min-[60em]:inline @min-[60em]:ml-2">{copy.above}</span> : null}
    </>
  );
}

/**
 * «KI-kostnad per Klasseøkt» (Story 15.6, FR-69, AD-22, UX-DR57): every saved Class session's AI
 * cost against its cost limit, per Game and per Student against the 0,10 and 0,50 USD targets,
 * each linking to the Class session's own page; the simulation budgets apart. Read again every
 * minute. Only an Admin sees it.
 */
export function AiCostPage() {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => (
        <PageShell user={user} title={copy.title} updatedAt={updatedAt} crumbs={COST_CRUMBS}>
          <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <Content />
        </PageShell>
      )}
    </GuardedPage>
  );
}

function Content() {
  const costs = useSessionCosts();
  const pageState = usePageState(costs, sessionCostsKey);
  if (pageState.phase === "loading" || pageState.phase === "slow") {
    return (
      <div className="mt-10">
        <Skeleton heading={false} rows={4} columns={5} />
        <LoadingNote visible={pageState.phase === "slow"} />
      </div>
    );
  }
  if (pageState.phase === "failed" || !costs.data) {
    return (
      <div className="mt-10 flex flex-col items-start gap-3">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button onClick={pageState.retry}>{nb.system.retry}</Button>
      </div>
    );
  }
  return <CostListView found={costs.data} />;
}

export function CostListView({ found }: { found: CostList }) {
  const columns = copy.columns;
  return (
    <>
      <section aria-labelledby="costs-title" className="mt-10 @container">
        <h2 id="costs-title" className="sr-only">
          {copy.title}
        </h2>
        {found.sessions.length === 0 ? (
          <p className={TEXT}>{copy.empty}</p>
        ) : (
          <table className={TABLE}>
            <thead className="@max-[60em]:hidden">
              <tr className="border-b border-axis">
                <th scope="col" className={HEAD}>
                  {columns.session}
                </th>
                <th scope="col" className={`${HEAD} text-right`}>
                  {columns.total}
                </th>
                <th scope="col" className={`${HEAD} text-right`}>
                  {columns.limit}
                </th>
                <th scope="col" className={`${HEAD} text-right`}>
                  {columns.perGame}
                </th>
                <th scope="col" className={`${HEAD} text-right`}>
                  {columns.perStudent}
                </th>
              </tr>
            </thead>
            <tbody className={BODY}>
              {found.sessions.map((item) => (
                <SessionRow key={item.class_session_id} item={item} />
              ))}
            </tbody>
          </table>
        )}
      </section>
      <Evaluations found={found} />
    </>
  );
}

function SessionRow({ item }: { item: SessionCostItem }) {
  const columns = copy.columns;
  return (
    <tr className={ROW} data-cost-session={item.class_session_id}>
      <Cell label={columns.session}>
        <Link href={adminAiCostPath(item.class_session_id)} standalone className="font-semibold [overflow-wrap:anywhere]">
          {item.label}
        </Link>
        {item.institution_name ? (
          <span className="block text-ink-secondary [overflow-wrap:anywhere]">{item.institution_name}</span>
        ) : null}
        {item.budget?.players_exhausted_at ? <span className="block font-semibold text-ink">{copy.reached}</span> : null}
      </Cell>
      <NumberCell label={columns.total}>{costText(item.total_usd)}</NumberCell>
      <NumberCell label={columns.limit}>{item.budget ? costText(item.budget.limit_usd) : copy.noBudget}</NumberCell>
      <NumberCell label={columns.perGame}>
        <TargetFigure amount={item.per_game_usd} above={item.per_game_above} />
      </NumberCell>
      <NumberCell label={columns.perStudent}>
        <TargetFigure amount={item.per_student_usd} above={item.per_student_above} />
      </NumberCell>
    </tr>
  );
}

/** The simulation budgets (AD-22): shown apart, so prototype spend never counts against a Class
 * session. */
function Evaluations({ found }: { found: CostList }) {
  const text = copy.evaluations;
  return (
    <section aria-labelledby="evaluation-costs-title" className="mt-12 @container">
      <h2 id="evaluation-costs-title" className="text-headline text-ink">
        {text.title}
      </h2>
      <p className={LEAD}>{text.lead}</p>
      {found.evaluations.length === 0 ? (
        <p className={TEXT}>{text.empty}</p>
      ) : (
        <table className={TABLE}>
          <thead className="@max-[60em]:hidden">
            <tr className="border-b border-axis">
              <th scope="col" className={HEAD}>
                {text.columns.model}
              </th>
              <th scope="col" className={`${HEAD} text-right`}>
                {text.columns.limit}
              </th>
              <th scope="col" className={`${HEAD} text-right`}>
                {text.columns.spent}
              </th>
            </tr>
          </thead>
          <tbody className={BODY}>
            {found.evaluations.map((item) => (
              <tr key={item.model_config_id} className={ROW}>
                <Cell label={text.columns.model}>
                  <span className="[overflow-wrap:anywhere]">{item.model_name}</span>
                </Cell>
                <NumberCell label={text.columns.limit}>{costText(item.budget.limit_usd)}</NumberCell>
                <NumberCell label={text.columns.spent}>{costText(item.budget.spent_usd)}</NumberCell>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
