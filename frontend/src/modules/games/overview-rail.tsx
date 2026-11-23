"use client";

import { useId, useRef, useState } from "react";

import { CostDistribution } from "@/components/charts/cost-distribution";
import { Link, LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";
import { messagePath } from "@/modules/identity/homes";
import { useMessageForm } from "@/modules/messaging/api";

import type { ClassOverview } from "./api";
import {
  aiLine,
  type ClassCost,
  costRows,
  costSummary,
  funnelRows,
  type OverviewGroup,
  roleBars,
  waitingElsewhere,
} from "./overview";

const copy = nb.overview.rail;

/** Until the rail is measured (a server render): its laptop width and the caption size. */
const FALLBACK = { width: 352, fontSize: 13 };

const whole = (value: string | number) => formatNumber(value, { decimals: 0 });

/**
 * The Oversikt's right rail (Story 7.6, UX-DR40, `08-laerer-oversikt.png`): «Venter ellers» with
 * the AI line, «Klassens kostnad» (not before the Start date) and «Trakt». Beside the wall from
 * 1024 px, under it below. Every number is the api's (AD-10); the rail reads the answer the page
 * shows, so it holds still with the rest while «Oppdater automatisk» is off. Story 13.6: under the
 * Trakt, the Lenke to the Meldingsskjema for the Students who have not met the requirement.
 */
export function OverviewRail({
  sessionId,
  data,
  groups,
  now,
  className,
  alertId = null,
}: {
  sessionId: string;
  data: ClassOverview;
  groups: readonly OverviewGroup[];
  now: number;
  className?: string;
  /** The Varselbånd's game, left out of «Venter ellers» (Story 7.11, UX-DR45). */
  alertId?: string | null;
}) {
  return (
    <aside aria-label={copy.label} className={cn("min-w-0 text-body-phone text-ink lg:text-body", className)} data-overview-rail="">
      <WaitingElsewhere data={data} groups={groups} now={now} alertId={alertId} />
      {data.before_start ? null : <ClassCostBlock data={data} />}
      <Funnel funnel={data.funnel} sessionId={sessionId} />
    </aside>
  );
}

function Section({ title, children, name }: { title: string; children: React.ReactNode; name: string }) {
  const id = useId();
  return (
    <section aria-labelledby={id} className="border-b border-hairline pb-6 not-first:mt-6" data-rail={name}>
      <h2 id={id} className="text-headline text-ink">
        {title}
      </h2>
      {children}
    </section>
  );
}

function WaitingElsewhere({
  data,
  groups,
  now,
  alertId,
}: {
  data: ClassOverview;
  groups: readonly OverviewGroup[];
  now: number;
  alertId: string | null;
}) {
  const rows = waitingElsewhere(groups, now, alertId);
  return (
    <Section title={copy.waiting.title} name="waiting">
      {rows.length === 0 ? (
        <p className="mt-2">{alertId ? copy.waiting.noneOther : copy.waiting.none}</p>
      ) : (
        <ul className="mt-2">
          {rows.map((row) => (
            <li key={row.id} data-game={row.id} className="grid grid-cols-[5rem_minmax(0,1fr)] gap-x-3 py-1">
              <span className="font-semibold">{row.game}</span>
              <span className="tabular-nums lining-nums [overflow-wrap:anywhere]">{row.who.join("; ")}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-caption text-ink-secondary tabular-nums lining-nums" data-ai-line="">
        {aiLine(data.ai)}
      </p>
    </Section>
  );
}

function ClassCostBlock({ data }: { data: ClassOverview }) {
  const cost = data.cost;
  return (
    <Section title={copy.cost.title} name="cost">
      {cost ? <CostPicture cost={cost} data={data} /> : <p className="mt-2">{copy.cost.none}</p>}
    </Section>
  );
}

function CostPicture({ cost, data }: { cost: ClassCost; data: ClassOverview }) {
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const [asTable, setAsTable] = useState(false);
  const rows = costRows(data.items);
  const bars = roleBars(cost);
  return (
    <>
      <p className="mt-1 text-caption text-ink-secondary tabular-nums lining-nums">{copy.cost.intro(cost.games)}</p>
      <div ref={box} className="mt-3 text-caption">
        {asTable ? (
          <table className="w-full border-collapse text-caption text-ink tabular-nums lining-nums" data-cost-table="">
            <caption className="sr-only">{copy.cost.tableCaption}</caption>
            <thead>
              <tr className="border-b border-axis text-ink-secondary">
                <th scope="col" className="py-1 text-left font-normal">
                  {copy.cost.gameColumn}
                </th>
                <th scope="col" className="py-1 pl-3 text-right font-normal">
                  {copy.cost.costColumn}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-hairline">
                  <th scope="row" className="py-1 text-left font-normal">
                    {row.game}
                  </th>
                  <td className="py-1 pl-3 text-right">{row.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <>
            <CostDistribution
              width={size.width}
              fontSize={size.fontSize}
              values={rows.map((row) => row.value)}
              median={Number(cost.median)}
              lower={Number(cost.lower_quartile)}
              upper={Number(cost.upper_quartile)}
              medianLabel={copy.cost.median(whole(cost.median))}
              title={copy.cost.chartTitle(cost.games)}
              formatTick={(value) => whole(value)}
            />
            <p className="mt-1 text-caption text-ink-secondary">{copy.cost.axis}</p>
          </>
        )}
      </div>
      <p className="mt-2 tabular-nums lining-nums" data-cost-summary="">
        {costSummary(cost)}
      </p>
      <button type="button" className={LINK_BUTTON} data-cost-toggle="" onClick={() => setAsTable((shown) => !shown)}>
        {asTable ? copy.cost.showChart : copy.cost.showTable}
      </button>
      <h3 className="mt-4 text-label text-ink">{copy.cost.rolesTitle}</h3>
      <ul className="mt-2" data-role-bars="">
        {bars.map((bar) => (
          <li key={bar.role} className="grid grid-cols-[6.5rem_minmax(0,1fr)_3.5rem] items-center gap-x-3 py-1">
            <span className="sr-only">{bar.reads}</span>
            <span aria-hidden="true">{bar.name}</span>
            {/* Drawn as top borders, so the bars are no text background. */}
            <span aria-hidden="true" className="flex h-3 min-w-0">
              <span className="block h-0 border-t-[0.75rem] border-lager" style={{ width: `${(bar.holding * 100).toFixed(2)}%` }} />
              <span className="block h-0 border-t-[0.75rem] border-restordre" style={{ width: `${(bar.backorder * 100).toFixed(2)}%` }} />
            </span>
            <span aria-hidden="true" className="text-right font-semibold tabular-nums lining-nums">
              {bar.amount}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 flex flex-wrap gap-x-4 text-caption text-ink-secondary tabular-nums lining-nums" data-cost-key="">
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-0 w-3 border-t-[0.75rem] border-lager" />
          {copy.cost.keyHolding(whole(cost.holding_cost))}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-block h-0 w-3 border-t-[0.75rem] border-restordre" />
          {copy.cost.keyBackorder(whole(cost.backorder_cost))}
        </span>
      </p>
    </>
  );
}

function Funnel({ funnel, sessionId }: { funnel: ClassOverview["funnel"]; sessionId: string }) {
  return (
    <Section title={copy.funnel.title} name="funnel">
      <ol className="mt-2" data-funnel="">
        {funnelRows(funnel).map((row) => (
          <li key={row.stage} data-stage={row.stage} className="grid grid-cols-[minmax(0,9rem)_3rem_minmax(0,1fr)] items-center gap-x-3 py-0.5">
            <span>{row.label}</span>
            <span className="text-right font-semibold tabular-nums lining-nums">{row.count}</span>
            <span aria-hidden="true" className="flex h-3 min-w-0">
              <span className="block h-0 border-t-[0.75rem] border-order-history" style={{ width: `${(row.share * 100).toFixed(2)}%` }} />
            </span>
          </li>
        ))}
      </ol>
      <NotMetLink sessionId={sessionId} />
    </Section>
  );
}

/**
 * «Send Melding til 12 som ikke har oppfylt kravet» (Story 13.6, FR-17, UX-DR54): the count is the
 * Meldingsskjema's own read for that recipient, under the same policy as sending a Message (AD-12).
 * Absent while it loads, when the Klasseøkt is not Obligatorisk, when everyone has met the
 * requirement, and for anyone the api refuses.
 */
function NotMetLink({ sessionId }: { sessionId: string }) {
  const found = useMessageForm(sessionId, { requirement: true });
  const count = found.data?.students ?? 0;
  if (count === 0) return null;
  return (
    <p className="mt-3">
      <Link href={messagePath(sessionId, { requirement: true })} standalone data-not-met-link="">
        {copy.funnel.notMet(count)}
      </Link>
    </p>
  );
}
