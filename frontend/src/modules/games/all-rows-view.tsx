"use client";

import { useEffect, useRef } from "react";

import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import type { SeatState } from "./api";
import { columnLines } from "./cost-panel";
import { CostPanel } from "./cost-panel-view";
import type { TypedOrder } from "./week-table";
import { WeekTable } from "./week-table-view";

const copy = nb.games.play.allRows;

/**
 * «Alle rader og kostnad» (Story 6.16, FR-23, UX-DR21, DESIGN.md, `05-spill.png` middle): the
 * phone's one tap to depth. A full screen on `paper` in place of the play screen, not an overlay:
 * «Alle rader, Uke 11» with «Lukk» at the right, the role and game under it, Graf over tabell with
 * every row (Lager, Restordre and «Sum, kr» too), the two column sums, then «Kostnad så langt».
 * On open, focus goes to the title, or to «Kostnad så langt» when its Lenke opened the screen;
 * «Lukk» (or Escape) hands back to the play screen, which keeps the typed Order and puts focus back on the
 * control that opened this one.
 */
export function AllRowsView({
  state,
  subtitle,
  nowOrder,
  typed,
  at,
  onClose,
}: {
  state: SeatState;
  /** «Grossist, Spill 17». */
  subtitle: string;
  nowOrder?: number;
  typed?: TypedOrder;
  /** Where the screen opens: its top, or «Kostnad så langt». */
  at: "top" | "cost";
  onClose: () => void;
}) {
  const title = useRef<HTMLHeadingElement>(null);
  const cost = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (at === "cost" && cost.current) {
      cost.current.focus({ preventScroll: true });
      cost.current.scrollIntoView({ block: "start" });
    } else {
      title.current?.focus({ preventScroll: true });
      window.scrollTo({ top: 0 });
    }
  }, [at]);
  // Escape closes the screen, as «Lukk» does.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div data-all-rows="" className="bg-paper">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          {/* 24 px, weight 700, as drawn (DESIGN.md → Alle rader og kostnad), not `title-phone`. */}
          <h1 ref={title} tabIndex={-1} className="text-[1.5rem] leading-[1.2] font-bold text-ink outline-none">
            {copy.title(state.week)}
          </h1>
          <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{subtitle}</p>
        </div>
        <button type="button" className={cn(LINK_BUTTON, "justify-end")} onClick={onClose} data-all-rows-close="">
          {copy.close}
        </button>
      </div>
      <div className="mt-6">
        <WeekTable state={state} nowOrder={nowOrder} typed={typed} allRows />
      </div>
      <dl className="mt-4 max-w-md text-body-phone text-ink tabular-nums lining-nums lg:text-body" data-column-lines="">
        {columnLines(state).map((line) => (
          <div key={line.label} className="flex flex-wrap justify-between gap-x-4 border-b border-hairline py-2">
            <dt>{line.label}</dt>
            <dd className="text-right">{line.sum}</dd>
          </div>
        ))}
      </dl>
      <CostPanel state={state} table="sumRow" headingRef={cost} className="mt-8 scroll-mt-4" />
    </div>
  );
}
