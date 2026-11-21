import type { ReactNode } from "react";

import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

const copy = nb.games.play.chain;

/** One Role's row of Kjedens regning, formatted by the caller: amounts as the api gave them. */
export type ChainBillRow = {
  /** The Role's key (`retailer`), for React and for tests. */
  role: string;
  /** «Grossist», or «Grossist (deg)» on the viewer's own row. */
  label: string;
  own: boolean;
  holding: string;
  backorder: string;
  total: string;
  /** The split bar: the holding and backlog parts as shares of the widest row, 0 … 1 each. */
  bar: { holding: number; backorder: number };
};

export type ChainBillTotal = { holding: string; backorder: string; total: string };

/**
 * Kjedens regning (`chain-bill`, Story 6.18, FR-28, UX-DR30, UX-DR73, DESIGN.md): a table with
 * Lager / Restordre / Sum and one row per Role, Detaljist to Fabrikk as the caller lists them,
 * never per name and never sorted by cost. Under each Role's name a split bar (`lager` | `restordre`)
 * whose numbers stand in the same row; the bar is `aria-hidden`. The viewer's own row is in weight
 * 600 with «(deg)»; «Kjeden», weight 700, stands under an `axis` rule. `extraRows` is the Debrief's
 * slot for its «Simulert» rows (Story 9.8), in a body of their own after «Kjeden»; it stays empty
 * on «Spillet er ferdig».
 */
export function ChainBill({
  rows,
  chain,
  extraRows,
  titleId,
  title = copy.bill,
  className,
}: {
  rows: readonly ChainBillRow[];
  chain: ChainBillTotal;
  extraRows?: ReactNode;
  titleId: string;
  /** The heading: «Kjedens regning», or the shared screen's «Kostnad, kr» (Story 9.13). */
  title?: string;
  className?: string;
}) {
  const cell = "py-1.5 pl-3 text-right align-top";
  const chainRow = (
    <tr data-chain-row="" className="border-t border-axis font-bold">
      <th scope="row" className="py-1.5 text-left">
        {copy.chain}
      </th>
      <td className={cell}>{chain.holding}</td>
      <td className={cell}>{chain.backorder}</td>
      <td className={cell}>{chain.total}</td>
    </tr>
  );
  return (
    <section aria-labelledby={titleId} data-chain-bill="" className={className}>
      <h2 id={titleId} className="text-headline text-ink">
        {title}
      </h2>
      {/* At 200 % text the four columns outgrow a phone: the table scrolls on its own, never the
          page (UX-DR75). */}
      <ScrollRegion labelledBy={titleId} className="mt-3">
        <table className="w-full border-collapse text-body-phone text-ink tabular-nums lining-nums lg:text-body">
          <caption className="sr-only">{copy.billCaption}</caption>
          <thead>
            <tr className="text-caption text-ink-secondary">
              <th scope="col" className="py-1 text-left font-normal">
                <span className="sr-only">{copy.role}</span>
              </th>
              <th scope="col" className={cn(cell, "font-normal")}>
                {copy.holding}
              </th>
              <th scope="col" className={cn(cell, "font-normal")}>
                {copy.backorder}
              </th>
              <th scope="col" className={cn(cell, "font-normal")}>
                {copy.sum}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.role}
                data-role={row.role}
                data-own={row.own ? "" : undefined}
                className={cn("relative", row.own ? "font-semibold" : "font-normal")}
              >
                <th scope="row" className={cn("pt-1.5 pb-3 text-left align-top", row.own ? "font-semibold" : "font-normal")}>
                  {row.label}
                  {/* Drawn as top borders across the whole row, so the bar is no text background
                      (as Kostnad så langt); the row is its positioned box. */}
                  <span aria-hidden="true" className="absolute inset-x-0 bottom-1.5 flex" data-bar="">
                    <span
                      data-bar-part="lager"
                      className="block h-0 border-t-[3px] border-lager"
                      style={{ width: `${(row.bar.holding * 100).toFixed(2)}%` }}
                    />
                    <span
                      data-bar-part="restordre"
                      className="block h-0 border-t-[3px] border-restordre"
                      style={{ width: `${(row.bar.backorder * 100).toFixed(2)}%` }}
                    />
                  </span>
                </th>
                <td className={cn(cell, "pb-3")}>{row.holding}</td>
                <td className={cn(cell, "pb-3")}>{row.backorder}</td>
                <td className={cn(cell, "pb-3")}>{row.total}</td>
              </tr>
            ))}
            {extraRows ? chainRow : null}
          </tbody>
          {/* The Debrief's rows come after «Kjeden», so they never read as part of its sum; a
              table may have nothing after its `tfoot`, so the sum row then ends the first body. */}
          {extraRows ? <tbody data-extra-rows="">{extraRows}</tbody> : <tfoot>{chainRow}</tfoot>}
        </table>
      </ScrollRegion>
    </section>
  );
}
