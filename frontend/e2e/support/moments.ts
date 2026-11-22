import week11 from "../../src/modules/games/fixtures/play-week-11.json";
import { week12 } from "./play";

/** Stand-in answers of Debrief step 4 (Story 9.7) with the api's shapes: three own moments of a
 * Grossist, each with its texts as the code renders them from the facts (version 1 of the moment
 * templates) and the Seat's Week as it saw it (the play screen's Uke 11 and 12 states). The api's
 * rendering and numbers are `backend/tests/debrief/test_explanation.py` and
 * `backend/tests/analysis/test_moments.py`. */
const code = (text: string) => ({ text, ai_generated: false, llm_call_id: null });

const others = [
  { role: "retailer", incoming_order: 8, inventory: 0, backlog: 4, supply_line: 12 },
  { role: "distributor", incoming_order: 4, inventory: 14, backlog: 0, supply_line: 22 },
  { role: "factory", incoming_order: 5, inventory: 9, backlog: 0, supply_line: 10 },
];

const later = week12().seat_state;

export const MOMENTS = {
  role: "wholesaler",
  student_orders: 30,
  mostly_ai: false,
  heading: code("Ditt øyeblikk: Uke 11. Du bestilte 24 med 16 på vei. Og hva det kostet kjeden."),
  moments: [
    {
      id: "moment:wholesaler:11",
      week: 11,
      order: 24,
      chosen_by: "pattern",
      heading: code("Uke 11. Du bestilte 24 med 16 på vei."),
      reckoning: code("Posisjon 0 − 20 + 16 = −4. Med 24 ble den 20."),
      later: code("I Uke 12 til 15 kostet leddet ditt 111,50 kr."),
      patterns: [
        code(
          "Mønster: Stor ordre etter mangel. En ordre godt over innkommende ordre i en uke med restordre, eller i en av de to ukene etter.",
        ),
        code(
          "Mønsteret hører til mekanismen etterspørsel som går tapt i ordrene: oppover i kjeden ser hvert ledd bare ordrer, ikke hva kundene bestilte.",
        ),
      ],
      others,
      seen: week11.seat_state,
    },
    {
      id: "moment:wholesaler:12",
      week: 12,
      order: 2,
      chosen_by: "order_gap",
      heading: code("Uke 12. Du bestilte 2 med 36 på vei."),
      reckoning: code("Posisjon 0 − 27 + 36 = 9. Med 2 ble den 11."),
      later: code("I Uke 13 til 16 kostet leddet ditt 98,00 kr."),
      patterns: [code("Ingen av mønstrene passer denne uka. Du bestilte 9 mindre enn ordren inn, som var 11.")],
      others,
      seen: later,
    },
    {
      id: "moment:wholesaler:36",
      week: 36,
      order: 4,
      chosen_by: "order_gap",
      heading: code("Uke 36. Du bestilte 4 med 8 på vei."),
      reckoning: code("Posisjon 3 − 0 + 8 = 11. Med 4 ble den 15."),
      later: code("Dette var spillets siste uke. Ingen senere uke kostet noe."),
      patterns: [code("Ingen av mønstrene passer denne uka. Du bestilte det samme som ordren inn, 4.")],
      others,
      seen: { ...later, week: 36 },
    },
  ],
};

/** Fewer than 10 own Orders: the game was played mostly by AI players (FR-44). */
export const MOSTLY_AI = { role: "wholesaler", student_orders: 3, mostly_ai: true, heading: null, moments: [] };
