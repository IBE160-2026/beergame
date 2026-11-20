"use client";

import { useLayoutEffect, useRef, useState } from "react";

import { ChainBand } from "@/components/charts/chain-band";
import { nb } from "@/copy/nb";
import type { components } from "@/lib/api/schema";

import { bandEnds, bandLabels, bandSentence, type BandState } from "./chain-band";

type Size = { width: number; fontSize: number };

/**
 * The play screen's Kjedebånd (Story 6.9, FR-23, UX-DR14, UX-DR15, UX-DR73): the Seat's own link,
 * drawn at the width it is given and the current text size, measured again whenever either
 * changes. Screen readers get the band as one sentence; the SVG is hidden from them. On a phone
 * it uses the chart gutter, as Graf over tabell does; on a laptop it keeps a modest width.
 */
export function ChainBandView({
  state,
  seatRoles,
  typed,
}: {
  state: BandState;
  /** A valid typed Order not yet confirmed (Story 6.11): a new box last on the pipe. */
  typed?: number;
  /** The game's Seats' Roles, Fabrikk first (UX-DR73), for the neighbour at each end. */
  seatRoles: readonly components["schemas"]["Role"][];
}) {
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<Size | null>(null);

  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const measure = () => {
      const next = { width: element.clientWidth, fontSize: parseFloat(getComputedStyle(element).fontSize) };
      setSize((was) => (was && was.width === next.width && was.fontSize === next.fontSize ? was : next));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const slots = state.supply_line_slots.map((slot) => slot.quantity);
  return (
    <div data-chain-band="" className="-mx-[calc(var(--spacing-gutter-phone)-var(--spacing-gutter-phone-chart))] mb-4 max-w-[28rem] lg:mx-0">
      <p className="sr-only">{bandSentence(state, typed)}</p>
      <div ref={box} aria-hidden="true" className="min-h-[6em] text-caption">
        {size && size.width > 0 ? (
          <ChainBand
            width={size.width}
            fontSize={size.fontSize}
            inventory={state.inventory}
            backlog={state.backlog}
            slots={slots}
            overdue={state.overdue}
            typed={typed}
            labels={bandLabels(state, bandEnds(state.role, seatRoles), typed)}
            title={nb.games.play.band.svg}
          />
        ) : null}
      </div>
    </div>
  );
}
