import type { BandLabels } from "@/components/charts/chain-band-layout";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import type { components } from "@/lib/api/schema";
import { roleName } from "@/modules/sessions/sessions";

import type { SeatState } from "./api";

type Role = components["schemas"]["Role"];

const copy = nb.games.play.band;
const terms = nb.terms;

/** The `seat_state` fields the Kjedebånd draws (Story 6.9); nothing else reaches it. */
export type BandState = Pick<
  SeatState,
  "role" | "week" | "incoming_order" | "incoming_delivery" | "shipped" | "inventory" | "backlog" | "supply_line" | "supply_line_slots" | "overdue"
>;

const labelled = (term: string, value: number) => copy.labelled(term, formatNumber(value));

/** The node's label(s): «Lager 12», «Restordre 13», both when both are held, «Lager 0» when
 * neither. */
function stockLabels(state: BandState): string[] {
  const found: string[] = [];
  if (state.inventory > 0 || state.backlog === 0) found.push(labelled(terms.inventory, state.inventory));
  if (state.backlog > 0) found.push(labelled(terms.backlog, state.backlog));
  return found;
}

/**
 * The ends of the Seat's link (UX-DR73): the neighbour Roles from the game's Seats, which come
 * Fabrikk first, so upstream is the one before. The Fabrikk's left end is «Produksjon», the
 * Detaljist's right end «Kundene».
 */
export function bandEnds(role: Role, seatRoles: readonly Role[]): { upstream: string; downstream: string } {
  const index = seatRoles.indexOf(role);
  const upstream = index > 0 ? seatRoles[index - 1] : undefined;
  const downstream = index >= 0 && index < seatRoles.length - 1 ? seatRoles[index + 1] : undefined;
  return {
    upstream: upstream ? roleName(upstream) : copy.production,
    downstream: downstream ? roleName(downstream) : copy.customers,
  };
}

/** Every label of the band, from the api's numbers as they came (AD-10). For the Detaljist,
 * «Ordre inn» is the customers' number of this Uke only (FR-14). A typed Order (Story 6.11) reads
 * «Din ordre 24» and «På vei 16 + 24»: the two numbers side by side, never summed. */
export function bandLabels(state: BandState, ends: { upstream: string; downstream: string }, typed?: number): BandLabels {
  const supplyLine = labelled(terms.supplyLine, state.supply_line);
  return {
    ...ends,
    order: typed === undefined ? copy.order : labelled(copy.order, typed),
    incoming: labelled(terms.incomingOrder, state.incoming_order),
    delivery: labelled(terms.incomingDelivery, state.incoming_delivery),
    shipped: labelled(terms.unitsShipped, state.shipped),
    stock: stockLabels(state),
    supplyLine: typed === undefined ? supplyLine : copy.withTyped(supplyLine, formatNumber(typed)),
    overdue: state.overdue > 0 ? formatNumber(state.overdue) : null,
  };
}

/** The band as one sentence for screen readers: «Ordre inn 8, Levering 4, Sendt 4, Restordre 13,
 * På vei 16» (NFR-6, UX-DR14). With a typed Order it ends «På vei 16 pluss 24» (Story 6.11). */
export function bandSentence(state: BandState, typed?: number): string {
  const supply = labelled(terms.supplyLine, state.supply_line);
  const supplyPart = state.overdue > 0 ? `${supply}, ${copy.overdue(formatNumber(state.overdue))}` : supply;
  return [
    labelled(terms.incomingOrder, state.incoming_order),
    labelled(terms.incomingDelivery, state.incoming_delivery),
    labelled(terms.unitsShipped, state.shipped),
    ...stockLabels(state),
    typed === undefined ? supplyPart : copy.withTypedRead(state.overdue > 0 ? `${supplyPart},` : supplyPart, formatNumber(typed)),
  ].join(", ");
}
