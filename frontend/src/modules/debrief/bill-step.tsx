"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { ChainBill } from "@/components/chain-bill";
import { ChainCostChart } from "@/components/chain-cost-chart";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { formatNumber } from "@/lib/number-format";
import { useGameResult } from "@/modules/games/api";
import { gameEnd } from "@/modules/games/result";
import { osloDateText } from "@/modules/sessions/dates";

import {
  aiHeld,
  backorderLine,
  type Debrief,
  finishDebrief,
  type MySummary,
  type SimulatedRow,
  summaryKey,
  useDebriefStep,
  useMySummary,
} from "./api";

const copy = nb.debrief.bill;
const LINE = "text-body-phone lg:text-body";
const money = (value: string) => formatNumber(value, { decimals: 2 });

/**
 * The end of Debrief step 4 (Story 9.8, FR-44, FR-47, UX-DR36, UX-DR73, `07-debrief.png`): under
 * the moments, Kjedens regning and Kjedens kostnad over tid as «Spillet er ferdig» drew them (the
 * shared components, from the game result: the same Decision log), with the viewer's row marked
 * «(deg)» and «Kjeden» under its rule. The Debrief's slot under «Kjeden» holds «Simulert, samme
 * kunder»: one row where only the viewer counts På vei and one where all four do, labelled
 * «Simulert» and followed by «Simulert viser sammenhengen, ikke en fasit.». Then the restordre
 * line and, when AI players held Seats in Weeks that cost something, their share. Every number is
 * the api's (AD-10). Last, «Fullfør Debriefen»; once finished, the line with its time stands in its
 * place and nothing on the page can be changed.
 */
export function BillStep({ debrief }: { debrief: Debrief }) {
  const step = useDebriefStep(debrief.id, 4, true);
  const bill = step.data?.bill ?? null;
  // The game result only once the step has answered: the same Decision log, as Story 6.18 drew it.
  const result = useGameResult(debrief.game_id, bill !== null);
  const id = useId();
  // Step 4's own read failing is the moments' to say; here only the bill's.
  if (bill && result.isError && !result.data) {
    return (
      <section aria-label={nb.games.play.chain.bill} data-debrief-bill="failed" className="mt-10 border-t border-axis pt-4">
        <div className="flex flex-col items-start gap-2">
          <ActionError message={copy.loadFailed} />
          <Button onClick={() => void result.refetch()}>{nb.system.retry}</Button>
        </div>
      </section>
    );
  }
  if (!bill || !result.data) return null;
  const model = gameEnd(result.data, debrief.role);
  const share = backorderLine(bill, copy);
  return (
    <div data-debrief-bill="" className="mt-10 max-w-md border-t border-axis pt-4">
      <ChainBill
        rows={model.rows}
        chain={model.chain}
        titleId={`${id}-bill`}
        extraRows={bill.simulated ? <SimulatedRows rows={bill.simulated.rows} /> : undefined}
      />
      <div className={`${LINE} mt-3 flex flex-col gap-2 text-ink`}>
        {bill.simulated ? (
          <>
            <p data-simulated-note="" className="text-caption text-ink-secondary">
              {copy.simulatedNote}
            </p>
            <p className="text-caption text-ink-secondary">{copy.simulatedRule}</p>
          </>
        ) : null}
        {share ? <p data-backorder-share="">{share}</p> : null}
        {aiHeld(bill) ? <p data-ai-share="">{copy.aiShare(bill.ai_held_share_percent!, formatNumber(bill.ai_held_cost, { kroner: true }))}</p> : null}
      </div>
      <ChainCostChart points={model.points} rows={model.weeks} endLabels={model.endLabels} className="mt-8" />
      <Finish debrief={debrief} />
    </div>
  );
}

/** «Simulert, samme kunder» in Kjedens regning's own columns: a label row, then the two rows. */
function SimulatedRows({ rows }: { rows: readonly SimulatedRow[] }) {
  const cell = "py-1.5 pl-3 text-right align-top";
  return (
    <>
      <tr data-simulated="">
        <th scope="rowgroup" colSpan={4} className="pt-4 pb-1 text-left text-label font-normal text-ink-secondary">
          {copy.simulated}
        </th>
      </tr>
      {rows.map((row) => (
        <tr key={row.counts_supply_line} data-simulated-row={row.counts_supply_line} className="font-normal">
          <th scope="row" className="py-1.5 text-left font-normal">
            {row.counts_supply_line === "own" ? copy.simulatedOwn : copy.simulatedAll}
          </th>
          <td className={cell}>{money(row.holding_cost)}</td>
          <td className={cell}>{money(row.backorder_cost)}</td>
          <td className={cell}>{money(row.total_cost)}</td>
        </tr>
      ))}
    </>
  );
}

/** «Fullfør Debriefen», or once finished the line with its time. After the press, focus moves to
 * that line, so a screen reader hears the Debrief is stored. */
function Finish({ debrief }: { debrief: Debrief }) {
  const summary = useMySummary(debrief.id, true);
  const queryClient = useQueryClient();
  const line = useRef<HTMLParagraphElement>(null);
  const finish = useAction({
    mutationFn: () => finishDebrief(debrief.id),
    messages: { debrief_incomplete: copy.incomplete, test_deadline_passed: copy.deadlinePassed },
    fallback: copy.failed,
    onSuccess: (stored: MySummary) => {
      // Stegene on Hjem follows through the `user` event the recorded step emits.
      queryClient.setQueryData(summaryKey(debrief.id), stored);
    },
  });
  const done = summary.data?.summary ?? null;
  const justFinished = finish.isSuccess;
  useEffect(() => {
    if (justFinished) line.current?.focus();
  }, [justFinished]);
  if (summary.isError && !summary.data) {
    return (
      <div data-debrief-finish="failed" className="mt-8 flex flex-col items-start gap-2">
        <ActionError message={copy.summaryFailed} />
        <Button onClick={() => void summary.refetch()}>{nb.system.retry}</Button>
      </div>
    );
  }
  if (!summary.data) return null;
  if (done) {
    return (
      <p ref={line} tabIndex={-1} role="status" data-debrief-finished="" className={`${LINE} mt-8 text-ink focus:outline-none`}>
        {copy.finished(osloDateText(done.finished_at))}
      </p>
    );
  }
  return (
    <div data-debrief-finish="" className="mt-8 flex flex-col gap-3">
      <p className={`${LINE} text-ink-secondary`}>{copy.finishHint}</p>
      <Button
        variant="primary"
        unavailable={finish.isPending}
        onClick={() => !finish.isPending && finish.mutate()}
        className="w-full lg:w-auto lg:self-start"
      >
        {copy.finish}
      </Button>
      <ActionError message={finish.errorMessage} />
    </div>
  );
}
