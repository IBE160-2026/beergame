import type { BandLabels } from "@/components/charts/chain-band-layout";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import type { components } from "@/lib/api/schema";
import { roleName } from "@/modules/sessions/sessions";

import type { SeatState } from "./api";

type Role = components["schemas"]["Role"];
type NeighbourNumber = components["schemas"]["NeighbourNumber"];

const copy = nb.games.play.band;
const terms = nb.terms;

/** The `seat_state` fields the Kjedebånd draws (Story 6.9); nothing else reaches it. */
export type BandState = Pick<
  SeatState,
  | "role"
  | "week"
  | "incoming_order"
  | "incoming_delivery"
  | "shipped"
  | "inventory"
  | "backlog"
  | "supply_line"
  | "supply_line_slots"
  | "overdue"
  | "neighbour_numbers"
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

/** The ends of the band: each end's label and, where Information visibility shows that
 * neighbour (Story 6.21), its numbers. */
export type BandEnds = {
  upstream: string;
  downstream: string;
  upstreamNumbers?: string[];
  downstreamNumbers?: string[];
};

/** A neighbour's end while its numbers show: «Distributør, Uke 11» and «Lager 12», «Restordre 3»,
 * as the api gave them (UX-DR24); null when the api gave none for that Role. */
function neighbourEnd(role: Role, numbers: readonly NeighbourNumber[]): { label: string; numbers: string[] } | null {
  const own = numbers.filter((number) => number.role === role);
  if (own.length === 0) return null;
  const value = (quantity: NeighbourNumber["quantity"]) => own.find((number) => number.quantity === quantity)?.value;
  const shown: string[] = [];
  const inventory = value("inventory");
  const backlog = value("backlog");
  if (inventory !== undefined) shown.push(labelled(terms.inventory, inventory));
  if (backlog !== undefined) shown.push(labelled(terms.backlog, backlog));
  return { label: copy.neighbour(roleName(role), formatNumber(own[0]!.week)), numbers: shown };
}

/**
 * The ends of the Seat's link (UX-DR73): the neighbour Roles from the game's Seats, which come
 * Fabrikk first, so upstream is the one before. The Fabrikk's left end is «Produksjon», the
 * Detaljist's right end «Kundene». A neighbour whose numbers `seat_state` holds (Information
 * visibility, Story 6.21) reads «Distributør, Uke 11» with its numbers; numbers of any Role that
 * is not an end neighbour are never drawn.
 */
export function bandEnds(role: Role, seatRoles: readonly Role[], numbers: readonly NeighbourNumber[] = []): BandEnds {
  const index = seatRoles.indexOf(role);
  const upstream = index > 0 ? seatRoles[index - 1] : undefined;
  const downstream = index >= 0 && index < seatRoles.length - 1 ? seatRoles[index + 1] : undefined;
  const up = upstream ? neighbourEnd(upstream, numbers) : null;
  const down = downstream ? neighbourEnd(downstream, numbers) : null;
  return {
    upstream: up ? up.label : upstream ? roleName(upstream) : copy.production,
    downstream: down ? down.label : downstream ? roleName(downstream) : copy.customers,
    ...(up ? { upstreamNumbers: up.numbers } : {}),
    ...(down ? { downstreamNumbers: down.numbers } : {}),
  };
}

/** Every label of the band, from the api's numbers as they came (AD-10). For the Detaljist,
 * «Ordre inn» is the customers' number of this Uke only (FR-14). A typed Order (Story 6.11) reads
 * «Din ordre 24» and «På vei 16 + 24»: the two numbers side by side, never summed. */
export function bandLabels(state: BandState, ends: BandEnds, typed?: number): BandLabels {
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
 * På vei 16» (NFR-6, UX-DR14). With a typed Order it ends «På vei 16 pluss 24» (Story 6.11). The
 * neighbours' numbers that `ends` holds follow, upstream first: «. Distributør, Uke 11: Lager 12,
 * Restordre 3» (Story 6.21). */
export function bandSentence(state: BandState, typed?: number, ends?: BandEnds): string {
  const supply = labelled(terms.supplyLine, state.supply_line);
  const supplyPart = state.overdue > 0 ? `${supply}, ${copy.overdue(formatNumber(state.overdue))}` : supply;
  const own = [
    labelled(terms.incomingOrder, state.incoming_order),
    labelled(terms.incomingDelivery, state.incoming_delivery),
    labelled(terms.unitsShipped, state.shipped),
    ...stockLabels(state),
    typed === undefined ? supplyPart : copy.withTypedRead(state.overdue > 0 ? `${supplyPart},` : supplyPart, formatNumber(typed)),
  ].join(", ");
  const neighbours: string[] = [];
  if (ends?.upstreamNumbers) neighbours.push(copy.neighbourRead(ends.upstream, ends.upstreamNumbers.join(", ")));
  if (ends?.downstreamNumbers) neighbours.push(copy.neighbourRead(ends.downstream, ends.downstreamNumbers.join(", ")));
  return [own, ...neighbours].join(". ");
}
