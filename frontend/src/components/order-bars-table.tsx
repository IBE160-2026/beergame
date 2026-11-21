"use client";

import { type ReactNode } from "react";

import { flowStep, OrderBars, OrderBarsLabels } from "@/components/charts/order-bars";
import { type GraphColumn, type GraphField, GraphOverTable } from "@/components/graph-over-table";
import { formatNumber } from "@/lib/number-format";
import { cn } from "@/lib/utils";

/** One Role, as the api gave it: its Orders per Uke, its Forsterkning (a decimal string such as
 * «7.600», null when customer demand never varied) and the first Uke with an Order of 10 or
 * more. */
export type OrderBarsRole = {
  key: string;
  /** «Fabrikk». */
  name: string;
  orders: readonly { week: number; order: number }[];
  /** Left out by a caller with no Forsterkning yet (Spillinnsikt before Story 9.5's wiring): with
   * no Role giving it, the Forsterkning column is not drawn (Story 7.8). */
  amplification?: string | null;
  firstLargeWeek: number | null;
};

/** One week column: 1.6 em, so 12 columns fit at 360 px; 1.65 em from 1024 px, so 36 Uker and the Forsterkning column fit the 1280 px laptop page without a scroll. */
const WEEK_COL = "w-[1.6em] min-w-[1.6em] px-[0.1em] text-center lg:w-[1.65em] lg:min-w-[1.65em]";
const ROW_LABEL =
  "sticky left-0 z-10 min-w-row-label-phone bg-paper pr-2 text-left align-middle font-normal text-ink lg:min-w-row-label-laptop";
/** Four rows of bars, each about three lines of `caption` high. */
const BARS_HEIGHT_EM = 12;
const FLOW = ["", "bg-flow-1 text-ink", "bg-flow-2 text-ink", "bg-flow-3 text-paper", "bg-flow-4 text-paper"] as const;

/**
 * Ordrestolper over the Rolle × Uke table (Story 9.5 for the Debrief step 3, reused by Spillinnsikt
 * in Story 7.8; UX-DR33, NFR-6, DESIGN.md `order-bars`): one Graf over tabell region, so bars and
 * numbers share their columns and scroll sideways together under a sticky label column. One row
 * per Role, in the order given (Fabrikk first). Each cell prints its Order on a `flow-*` step;
 * Forsterkning stands at the right of each Role's row in `figure-amplification`. `ownRole` marks
 * the viewer's Role (`ink` bars, weight 600); staff leave it unset. `chosenWeek` puts the
 * Ukeskrubber's dashed line across the bars and bolds that Uke. Every number is the api's.
 */
export function OrderBarsTable({
  label,
  roles,
  ownRole,
  chosenWeek,
  labelledBy,
  caption,
  texts,
}: {
  /** The scroll region's accessible name. */
  label: string;
  roles: readonly OrderBarsRole[];
  ownRole?: string;
  chosenWeek?: number;
  labelledBy?: string;
  /** The line over the bars (a key); read by screen readers. */
  caption?: ReactNode;
  texts: {
    week: string;
    /** «Uke 6», at a Role's first large Order. */
    weekLabel: (week: number) => string;
    /** «Forsterkning», the trailing column's header. */
    amplification: string;
    /** «(deg)» after the own Role. */
    own: string;
    /** For a Role with no Forsterkning (demand never varied). */
    none: string;
    svg: string;
    axisSvg: string;
    swipe: string;
  };
}) {
  const weeks = [...new Set(roles.flatMap((role) => role.orders.map((o) => o.week)))].sort((a, b) => a - b);
  const columns: GraphColumn[] = weeks.map((week) => ({ week, when: "past", phone: true }));
  const largest = Math.max(0, ...roles.flatMap((role) => role.orders.map((o) => o.order)));
  const byWeek = roles.map((role) => new Map(role.orders.map((o) => [o.week, o.order])));
  const amplified = roles.some((role) => role.amplification !== undefined);
  const nameOf = (role: OrderBarsRole) => (role.key === ownRole ? `${role.name} ${texts.own}` : role.name);
  const field: GraphField = {
    key: "orders",
    caption,
    heightEm: BARS_HEIGHT_EM,
    render: (size) => {
      const index = new Map(size.columns.map((column, i) => [column.week, i]));
      return {
        plot: (
          <OrderBars
            width={size.width}
            height={size.height}
            fontSize={size.fontSize}
            xs={size.xs}
            columnWidth={size.columnWidth}
            chosen={chosenWeek === undefined ? null : (index.get(chosenWeek) ?? null)}
            title={texts.svg}
            rows={roles.map((role, r) => {
              const at = role.firstLargeWeek === null ? undefined : index.get(role.firstLargeWeek);
              return {
                own: role.key === ownRole,
                orders: size.columns.map((column) => byWeek[r]!.get(column.week) ?? null),
                firstLarge: at === undefined || role.firstLargeWeek === null ? null : { index: at, text: texts.weekLabel(role.firstLargeWeek) },
              };
            })}
          />
        ),
        axis: (
          <OrderBarsLabels
            width={size.labelWidth}
            height={size.height}
            fontSize={size.fontSize}
            title={texts.axisSvg}
            labels={roles.map((role) => ({ text: nameOf(role), own: role.key === ownRole }))}
          />
        ),
      };
    },
  };
  return (
    <GraphOverTable
      label={label}
      columns={columns}
      fields={[field]}
      labelledBy={labelledBy}
      swipe={texts.swipe}
      head={
        <tr className="border-b border-axis">
          <th scope="row" className={ROW_LABEL}>
            {texts.week}
          </th>
          {weeks.map((week) => (
            <th
              key={week}
              scope="col"
              data-col={week}
              aria-current={week === chosenWeek ? "true" : undefined}
              className={cn(WEEK_COL, "h-row-phone font-normal text-ink-muted lg:h-row-laptop", week === chosenWeek && "font-bold text-ink")}
            >
              <span className="sr-only">{texts.week} </span>
              {week}
            </th>
          ))}
          {amplified ? (
            <th scope="col" className="pl-3 text-right align-middle text-caption font-normal whitespace-nowrap text-ink-secondary">
              {texts.amplification}
            </th>
          ) : null}
        </tr>
      }
      body={roles.map((role, r) => (
        <tr key={role.key} data-role={role.key} className="border-b border-paper">
          <th scope="row" className={cn(ROW_LABEL, role.key === ownRole && "font-semibold")}>
            {nameOf(role)}
          </th>
          {weeks.map((week) => {
            const order = byWeek[r]!.get(week);
            const flow = order === undefined ? undefined : flowStep(order, largest);
            return (
              <td
                key={week}
                data-flow={flow}
                className={cn(WEEK_COL, "h-row-phone lg:h-row-laptop", flow === undefined ? "" : FLOW[flow])}
              >
                {order === undefined ? "" : formatNumber(order)}
              </td>
            );
          })}
          {amplified ? (
            <td data-amplification="" className="pl-3 text-right align-middle text-figure-amplification leading-none whitespace-nowrap text-ink">
              {role.amplification == null ? texts.none : `${formatNumber(role.amplification, { decimals: 1 })}×`}
            </td>
          ) : null}
        </tr>
      ))}
    />
  );
}
