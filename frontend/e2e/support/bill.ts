import { MOMENTS } from "./moments";

/** Stand-in answers of the end of Debrief step 4 (Story 9.8) with the api's shapes: the lines
 * under Kjedens regning (the result fixture's chain: 1 365,00 of 2 266,00 is restordre, 60 %),
 * an AI-held share and the two «Simulert, samme kunder» rows; a finished summary; and the staff's
 * read of it. The api's numbers are `backend/tests/debrief/test_explanation.py` and
 * `backend/tests/analysis/test_simulated.py`. */
export const BILL = {
  role: "wholesaler",
  total_cost: "2266.0000",
  backorder_cost: "1365.0000",
  backorder_share_percent: 60,
  backorder_costs_double: true,
  ai_held_cost: "271.5000",
  ai_held_share_percent: 12,
  simulated: {
    params_id: "placeholder-unverified",
    rows: [
      { counts_supply_line: "own", holding_cost: "1027.50", backorder_cost: "479.50", total_cost: "1507.00" },
      { counts_supply_line: "all", holding_cost: "903.00", backorder_cost: "438.00", total_cost: "1341.00" },
    ],
  },
};

const ANSWERS = [
  { question_id: "feelings", prompt: "Hvordan var det å spille?", text: "Stressende." },
  { question_id: "evidence", prompt: "Hva i tallene viser det?", text: "Fabrikken svingte mest." },
  { question_id: "structure", prompt: "Hva i kjeden gjorde det slik?", text: "Forsinkelser." },
];

export const SUMMARY = {
  fact_set_id: "01a1aaaa-0000-7000-8000-0000000009f5",
  finished_at: "2026-11-21T13:05:00Z",
  late: false,
  moments: MOMENTS.moments.map(({ id, week, heading, reckoning, later, patterns }) => ({
    id,
    week,
    heading,
    reckoning,
    later,
    patterns,
  })),
  reflection: ANSWERS,
  quiz_attempts: 0,
  quiz_passed_at: null,
};

export const STAFF_SUMMARY = {
  student_id: "01a1aaaa-0000-7000-8000-0000000009e1",
  game_id: "01a1aaaa-0000-7000-8000-0000000009a7",
  game_number: 17,
  role: "wholesaler",
  explanation: { text: "Restordren vokste, så jeg bestilte mye.", length: 39, saved_at: "2026-11-21T12:00:00Z" },
  summary: { ...SUMMARY, late: true },
};
