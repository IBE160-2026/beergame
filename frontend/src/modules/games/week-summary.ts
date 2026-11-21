import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { PlayTurn, SeatState } from "./api";

const copy = nb.games.play.summary;

export type SummaryRow = { label: string; value: string };

/** The Uke-overgang (Story 6.15, UX-DR23, DESIGN.md → `week-summary`, `06-spilldynamikk.png` D):
 * what the Uke just run did to the Seat, every number as the api sent it. */
export type WeekSummary = {
  /** «Uke 11 er ferdig regnet». */
  title: string;
  /** Levering, Ordre inn and Sendt of the new Uke, then «Lager a blir b» / «Restordre a blir b». */
  rows: SummaryRow[];
  /** «Denne uka: 20 restordre × 1,00 = 20,00 kr». */
  cost: string;
  /** The whole summary as one sentence each line, for the polite announcement. */
  spoken: string;
};

/**
 * The summary of the Uke before the open one, or null when there is none to show: in Uke 1 (no
 * Uke before), and in a free Uke once the Seat's own Order is placed (it stays above the Ordrefelt
 * until then, [ASSUMPTION], Story 6.15). In a Veiledet uke it stays all Uke. The «a blir b» pairs
 * are the last `history` row and the open Uke's values; a row shows when either is not zero (with
 * both Lager and Restordre at zero, the Lager row). The cost line lists the Uke's cost lines with
 * units, joined by « + ».
 */
export function weekSummary(state: SeatState, turn: PlayTurn): WeekSummary | null {
  const before = state.history.at(-1);
  if (!before) return null;
  if (!turn.guided && turn.order != null) return null;
  const n = (value: number) => formatNumber(value);
  const rows: SummaryRow[] = [
    { label: nb.terms.incomingDelivery, value: n(state.incoming_delivery) },
    { label: nb.terms.incomingOrder, value: n(state.incoming_order) },
    { label: nb.terms.unitsShipped, value: n(state.shipped) },
  ];
  const inventory = before.inventory !== 0 || state.inventory !== 0;
  const backlog = before.backlog !== 0 || state.backlog !== 0;
  if (inventory || !backlog) {
    rows.push({ label: nb.terms.inventory, value: copy.change(n(before.inventory), n(state.inventory)) });
  }
  if (backlog) {
    rows.push({ label: nb.terms.backlog, value: copy.change(n(before.backlog), n(state.backlog)) });
  }
  const parts = state.cost_lines
    .filter((line) => line.units > 0)
    .map((line) =>
      (line.kind === "holding" ? copy.holdingPart : copy.backorderPart)(n(line.units), formatNumber(line.rate, { decimals: 2 })),
    );
  const cost = copy.weekCost(parts, formatNumber(state.week_cost, { kroner: true }));
  const title = copy.done(before.week);
  const spoken = [`${title}.`, ...rows.map((row) => `${row.label} ${row.value}.`), `${cost}.`].join(" ");
  return { title, rows, cost, spoken };
}
