"use client";

import { useId } from "react";

import { nb } from "@/copy/nb";

import type { PlayTurn } from "./api";

const copy = nb.games.play.order;

/**
 * Ordrefelt (DESIGN.md → Ordrefelt, UX-DR20, UX-DR62). Story 6.10 builds its first state: in a
 * Veiledet uke the Order is fixed and placed for the Student, so the field shows it read-only on
 * `future-tint` with the reason under it, and there is no button. Its editable states come in Story
 * 6.11; outside a Guided Week it renders nothing until then. Nothing here says how many Veiledede
 * uker remain (FR-14).
 */
export function OrderField({ week, turn }: { week: number; turn: PlayTurn }) {
  const id = useId();
  if (!turn.guided || turn.order == null) return null;
  return (
    <div className="mt-8 mb-8 max-w-md lg:mt-0" data-order-field="guided">
      <label htmlFor={`${id}-input`} className="block text-label text-ink">
        {copy.label(week)}
      </label>
      <input
        id={`${id}-input`}
        type="text"
        inputMode="numeric"
        readOnly
        aria-describedby={`${id}-guided`}
        value={String(turn.order)}
        className="mt-2 block min-h-order-input-height w-full rounded-sm border border-ink-muted bg-future-tint px-3 text-center text-figure-order text-ink-muted tabular-nums lining-nums"
      />
      <p id={`${id}-guided`} className="mt-2 text-caption text-ink-secondary">
        {copy.guided}
      </p>
    </div>
  );
}
