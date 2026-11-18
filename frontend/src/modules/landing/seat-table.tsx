import { nb } from "@/copy/nb";
import { cn } from "@/lib/utils";

import { DEMO_ROWS, DEMO_SEAT } from "./demo-seat";

const copy = nb.landing.seat;

const LABELS: Record<(typeof DEMO_ROWS)[number][0], string> = {
  incomingOrder: nb.terms.incomingOrder,
  incomingDelivery: nb.terms.incomingDelivery,
  netInventory: nb.terms.netInventory,
  supplyLine: nb.terms.supplyLine,
  order: copy.yourOrder,
};

/**
 * The Netto lager cell's matrix step (DESIGN.md → Matrix steps): bins |v| 1–9 / 10–19 / 20–34 /
 * 35+, blue above zero, red below; `ink` text on steps 1–2, `paper` on 3–4. Literal class names so
 * Tailwind finds them.
 */
const NET_POS = ["bg-net-pos-1", "bg-net-pos-2", "bg-net-pos-3 text-paper", "bg-net-pos-4 text-paper"];
const NET_NEG = ["bg-net-neg-1", "bg-net-neg-2", "bg-net-neg-3 text-paper", "bg-net-neg-4 text-paper"];

function netStep(v: number): string {
  if (v === 0) return "bg-net-zero";
  const a = Math.abs(v);
  const bin = a < 10 ? 0 : a < 20 ? 1 : a < 35 ? 2 : 3;
  return (v > 0 ? NET_POS : NET_NEG)[bin];
}

/**
 * The Landing's Seat figure (Story 3.13, UX-DR70, UX-DR3): one Seat in a Veiledet uke from the
 * synthetic fixture, as an HTML week table with tabular lining figures and the «Demodata» label.
 * Weeks are columns, as in the game's table under the graph; Story 6.8 puts the shared graph
 * over this same table. Net stock carries its matrix step, the current week its weight.
 */
export function SeatTable() {
  const current = DEMO_SEAT.currentWeek;
  return (
    <figure className="m-0">
      <table className="w-full max-w-xl border-collapse text-right text-table-cell tabular-nums lining-nums text-ink lg:text-table-cell-laptop">
        <caption className="mb-3 text-left text-label font-semibold text-ink">{copy.caption}</caption>
        <thead>
          <tr className="border-b border-axis">
            <th scope="col" className="py-2 pr-3 text-left font-normal text-ink-secondary">
              {copy.week}
            </th>
            {DEMO_SEAT.weeks.map((w) => (
              <th
                key={w.week}
                scope="col"
                className={cn("py-2 pl-2", w.week === current ? "font-bold" : "font-normal text-ink-secondary")}
              >
                {w.week}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {DEMO_ROWS.map(([key, value]) => (
            <tr key={key} className="border-b border-hairline">
              <th scope="row" className="py-2 pr-3 text-left font-normal whitespace-nowrap">
                {LABELS[key]}
              </th>
              {DEMO_SEAT.weeks.map((w) => (
                <td
                  key={w.week}
                  className={cn(
                    "py-2 pl-2",
                    key === "netInventory" && netStep(value(w)),
                    w.week === current && "font-bold",
                  )}
                >
                  {value(w)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <figcaption className="mt-2 flex max-w-xl flex-wrap justify-between gap-x-4 text-caption text-ink-muted">
        <span>{copy.ownNumbers}</span>
        <span>{copy.demoData}</span>
      </figcaption>
    </figure>
  );
}
