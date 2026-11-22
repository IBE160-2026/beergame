/** A stand-in answer of Debrief step 2 (Story 9.4), as `07-debrief.png` draws it: the Classic
 * demand (4, then 8 from Uke 5), the Orders that reached a Grossist, and its own Orders with 24 in
 * Uke 11. */
const INCOMING = [4, 4, 4, 4, 4, 6, 10, 11, 10, 8, 11, 10, 10, 8, 11, 12, 9, 6, 9, 9, 10, 8, 8, 9, 9, 7, 6, 5, 5, 6, 6, 7, 8, 7, 8, 6];
const ORDERS = [4, 4, 4, 4, 4, 4, 4, 4, 4, 8, 24, 16, 16, 13, 12, 15, 14, 15, 8, 9, 10, 12, 8, 6, 6, 3, 3, 1, 2, 2, 3, 6, 7, 9, 9, 6];

export const REVEAL = {
  heading: "Kundene bestilte 4, så 8. Etter det endret de seg aldri.",
  template_id: "demand-step",
  role: "wholesaler",
  weeks: INCOMING.map((incoming, i) => ({ week: i + 1, demand: i < 4 ? 4 : 8, incoming_order: incoming, order: ORDERS[i]! })),
  largest_order: { week: 11, order: 24 },
};
