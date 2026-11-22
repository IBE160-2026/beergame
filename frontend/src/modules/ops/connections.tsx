"use client";

import { useId } from "react";

import { ScrollRegion } from "@/components/scroll-region";
import { Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { formatClock } from "@/lib/connection";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";
import { formatTime } from "@/modules/admin/audit";

import { useConnectionBudget } from "./api";
import { configuredText, poolerText, runningText } from "./connection-budget";

const copy = nb.admin.operations.connections;

const TABLE =
  "w-full max-w-2xl border-collapse text-left text-table-cell tabular-nums lining-nums text-ink lg:text-table-cell-laptop";
const HEAD = "border-b border-axis py-2 pr-4 align-bottom text-label font-semibold text-ink";
const CELL = "border-b border-hairline py-1.5 pr-4";
const NUM = "text-right";
const LINE = "mt-3 max-w-2xl text-body-phone lg:text-body";

/**
 * «Databasetilkoblinger» on «Drift» (Story 15.9, NFR-3, NFR-4): per process the connections its
 * latest start set aside against the written budget, the sum, and the pooler check against what a
 * deploy overlap needs. Counts only. Read again with the page every 30 s; a failed read keeps the
 * last figures.
 */
export function ConnectionBudgetSection() {
  const budget = useConnectionBudget();
  const id = useId();
  const captionId = useId();
  const found = budget.data;
  return (
    <section aria-labelledby={id} className="mt-12" data-connection-budget="">
      <h2 id={id} className="text-headline text-ink">
        {copy.title}
      </h2>
      <p className="mt-2 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
      {budget.isPending ? <Skeleton heading={false} rows={3} columns={4} /> : null}
      {budget.isError && !found ? (
        <p role="alert" className={cn(LINE, "text-restordre")}>
          {nb.system.pageError}
        </p>
      ) : null}
      {budget.isError && found ? (
        <p role="status" className={cn(LINE, "text-ink-secondary")}>
          {nb.admin.operations.failed(formatClock(budget.dataUpdatedAt))}
        </p>
      ) : null}
      {found ? (
        <>
          <div className="mt-4">
            <ScrollRegion labelledBy={captionId}>
              <table className={TABLE}>
                <caption id={captionId} className="sr-only">
                  {copy.tableRegion}
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className={HEAD}>
                      {copy.columns.process}
                    </th>
                    <th scope="col" className={cn(HEAD, NUM)}>
                      {copy.columns.budget}
                    </th>
                    <th scope="col" className={cn(HEAD, NUM)}>
                      {copy.columns.configured}
                    </th>
                    <th scope="col" className={HEAD}>
                      {copy.columns.reported}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {found.processes.map((item) => (
                    <tr key={item.process} data-process={item.process}>
                      <th scope="row" className={cn(CELL, "font-normal")}>
                        {item.process}
                      </th>
                      <td className={cn(CELL, NUM)}>{formatNumber(item.budget.total)}</td>
                      <td
                        className={cn(
                          CELL,
                          NUM,
                          item.over_budget && "font-semibold text-restordre",
                          !item.configured && "text-ink-secondary",
                        )}
                      >
                        {configuredText(item)}
                      </td>
                      <td className={cn(CELL, "text-ink-secondary")}>
                        {item.reported_at ? formatTime(item.reported_at) : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <th scope="row" className="py-2 pr-4 font-semibold">
                      {copy.sum}
                    </th>
                    <td className={cn("py-2 pr-4 font-semibold", NUM)}>{formatNumber(found.budget_total)}</td>
                    <td className={cn("py-2 pr-4 font-semibold", NUM)}>{formatNumber(found.configured_total)}</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </ScrollRegion>
          </div>
          <p
            className={cn(LINE, found.running === "over" ? "font-semibold text-restordre" : "text-ink")}
            data-running={found.running}
          >
            {runningText(found)}
          </p>
          <p
            className={cn(LINE, found.pooler.status === "failed" ? "font-semibold text-restordre" : "text-ink")}
            data-pooler={found.pooler.status}
          >
            {poolerText(found)}
          </p>
          <p className={cn(LINE, "text-ink-secondary")}>
            {copy.need(
              formatNumber(found.budget_total),
              formatNumber(found.overlap_total),
              formatNumber(found.pooler.required),
            )}
          </p>
        </>
      ) : null}
    </section>
  );
}
