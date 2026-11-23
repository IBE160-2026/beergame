import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";
import { DEBRIEF_PATH, studentDebriefPath } from "@/modules/identity/homes";

import {
  aiHeld,
  aloneAt,
  answerText,
  backorderLine,
  type Bill,
  type Chain,
  currentQuestion,
  type Debrief,
  debriefView,
  downstreamRole,
  excludedIds,
  explanationDraftField,
  type FollowUp,
  type FollowUpAnswer,
  followUpDraftField,
  type GroupMember,
  hasText,
  lockedLine,
  namesText,
  type Quiz,
  type QuizAttempt,
  quizAnswers,
  type Reflection,
  reflectionDone,
  reach,
  reflectionDraftField,
  type SessionQuiz,
  waitMinutes,
  withFollowUp,
  type SharedChain,
  sharedCostRows,
  sharedNetRows,
  sharedPath,
  shownText,
  waitingFor,
  withAnswer,
  withAttempt,
} from "./api";
import { amplificationLine, chainBandInput, chainReading } from "./chain-step";

const copy = nb.debriefEntry;

const DEBRIEF: Debrief = {
  id: "d1",
  class_session_id: "s1",
  game_id: "g1",
  game_number: 17,
  makeup: false,
  role: "wholesaler",
  step: 1,
};

describe("the Debrief page's state (Story 9.2)", () => {
  it("comes from the api's answer or refusal code alone", () => {
    expect(debriefView(DEBRIEF, null)).toBe("open");
    expect(debriefView(undefined, "debrief_not_open")).toBe("notOpen");
    expect(debriefView(undefined, "debrief_held")).toBe("held");
    expect(debriefView(undefined, "forbidden")).toBe("denied");
    expect(debriefView(undefined, "network_error")).toBe("other");
    expect(debriefView(undefined, null)).toBe("other");
  });

  it("is reached at the Class session's own path", () => {
    expect(DEBRIEF_PATH("a/b")).toBe("/debrief/a%2Fb");
  });

  it("words the title, step 1 and the locked states without a count of games", () => {
    expect(copy.title(17)).toBe("Debrief, Spill 17");
    expect(copy.firstStep).toBe("Skriv Forklaringen først");
    expect(copy.stepOf(1, 5)).toBe("Steg 1 av 5");
    for (const line of [copy.notOpen, copy.held, nb.games.play.end.held]) {
      expect(line).not.toMatch(/\d|!/);
    }
  });
});

describe("the Explanation (Story 9.3)", () => {
  const words = copy.explanation;

  it("may be sent only with more than white space", () => {
    expect(hasText("")).toBe(false);
    expect(hasText("  \n\t ")).toBe(false);
    expect(hasText(" Lageret svingte. ")).toBe(true);
  });

  it("keeps its draft per Class session", () => {
    expect(explanationDraftField("s1")).not.toBe(explanationDraftField("s2"));
  });

  it("uses the spine's words and says nothing of customers or demand before the reveal", () => {
    expect([words.netTitle, words.prompt, words.send, words.showTable, words.failed]).toEqual([
      "Ditt netto lager, hele spillet",
      "Hvorfor svingte lageret ditt?",
      "Send Forklaring",
      "Vis som tabell",
      "Det ble ikke lagret. Prøv igjen.",
    ]);
    const all = Object.values(words)
      .map((value) => (typeof value === "function" ? value(1) : value))
      .join(" ");
    expect(all).not.toMatch(/kunde|etterspørsel|!/i);
  });
});

describe("the reveal (Story 9.4)", () => {
  it("names the Role whose Orders reached the Seat, and none for the Detaljist", () => {
    expect(downstreamRole("factory")).toBe("distributor");
    expect(downstreamRole("distributor")).toBe("wholesaler");
    expect(downstreamRole("wholesaler")).toBe("retailer");
    expect(downstreamRole("retailer")).toBeNull();
  });

  it("words the band and table as the spine does, and names the exercise only after the reveal", () => {
    const reveal = nb.debrief.reveal;
    expect(reveal.incomingKey).toBe("Ordre inn: det eneste du så");
    expect(reveal.largestOrder("24", 11)).toBe("Din ordre, 24 i Uke 11");
    expect(reveal.demandLabel("8")).toBe("Kundenes etterspørsel: 8");
    expect(Object.values(reveal.rows)).toEqual(["Kundene", "Ordre inn", "Din ordre"]);
    expect(reveal.named).toBe("Øvelsen heter Beer Game.");
    expect(JSON.stringify(nb.debriefEntry)).not.toMatch(/beer|bullwhip/i);
  });
});

const week = (w: number, order: number, inventory: number, backlog: number, supply = 0, incoming = 4) => ({
  week: w,
  order,
  incoming_order: incoming,
  inventory,
  backlog,
  supply_line: supply,
});

const CHAIN: Chain = {
  own_role: "wholesaler",
  last_week: 2,
  large_order: 10,
  roles: [
    { role: "factory", amplification: "7.600", first_large_order_week: 2, capacity: null, weeks: [week(1, 4, 12, 0), week(2, 22, 0, 3, 50)] },
    { role: "distributor", amplification: "6.000", first_large_order_week: 2, capacity: null, weeks: [week(1, 4, 12, 0), week(2, 12, 0, 34, 52)] },
    { role: "wholesaler", amplification: "4.100", first_large_order_week: 2, capacity: 12, weeks: [week(1, 4, 12, 0), week(2, 12, 2, 19)] },
    { role: "retailer", amplification: null, first_large_order_week: null, capacity: null, weeks: [week(1, 4, 0, 0), week(2, 8, 12, 0, 13, 8)] },
  ],
};

describe("the whole chain at a Uke (Story 9.5)", () => {
  it("reads the chain Fabrikk first, both held numbers of a capped Seat, then the customers", () => {
    expect(chainReading(CHAIN, 2)).toBe(
      "Uke 2. Fabrikk: restordre 3, ordre 22. Distributør: restordre 34, ordre 12. Grossist: lager 2, restordre 19, ordre 12. Detaljist: lager 12, ordre 8. Kundene: ordre 8.",
    );
    expect(chainReading(CHAIN, 1)).toContain("Detaljist: lager 0, ordre 4.");
  });

  it("gives the band the api's numbers at the Uke, one bar scale for the game", () => {
    const input = chainBandInput(CHAIN, 2, 360, 13);
    expect(input.nodes.map((n) => [n.label, n.numbers, n.own])).toEqual([
      ["Fabrikk", ["Restordre 3"], false],
      ["Distributør", ["Restordre 34"], false],
      ["Grossist", ["Lager 2", "Restordre 19"], true],
      ["Detaljist", ["Lager 12"], false],
    ]);
    expect(input.orders).toEqual(["22", "12", "12", "8", "8"]);
    expect(input.supplyLines).toEqual(["50", "52", null, "13"]);
    expect(input.maxUnits).toBe(34);
    expect([input.upstream, input.downstream]).toEqual(["Produksjon", "Kundene"]);
  });

  it("states Forsterkning from the customers' end up, with a dash where demand never varied", () => {
    expect(amplificationLine(CHAIN)).toBe("Forsterkning fra kundene og oppover: Detaljist –, Grossist 4,1×, Distributør 6,0×, Fabrikk 7,6×.");
    expect(nb.debrief.chain.heading).toBe("Hele kjeden: svingningene vokser oppstrøms og kommer senere");
    expect(nb.debrief.chain.at(15)).toBe("Kjeden i Uke 15. Dra i skrubberen for å spole.");
  });
});

describe("the reflection questions (Story 9.6)", () => {
  const answer = { text: "Stressende.", length: 11, saved_at: "2026-11-21T12:00:00Z" };
  const REFLECTION: Reflection = {
    version: 1,
    questions: [
      { id: "feelings", kind: "feelings", prompt: "Hvordan?", hint: null, answer },
      { id: "evidence", kind: "evidence", prompt: "Hva?", hint: null, answer: null },
      { id: "structure", kind: "structure", prompt: "Hvorfor?", hint: "Struktur.", answer: null },
    ],
  };

  it("asks the first unanswered question, and none once all are answered", () => {
    expect(currentQuestion(REFLECTION)?.id).toBe("evidence");
    const evidence = { ...REFLECTION.questions[1]!, answer };
    const next = withAnswer(REFLECTION, evidence);
    expect(currentQuestion(next)?.id).toBe("structure");
    expect(next.questions[1]).toBe(evidence);
    expect(REFLECTION.questions[1]!.answer).toBeNull();
    expect(currentQuestion(withAnswer(next, { ...REFLECTION.questions[2]!, answer }))).toBeNull();
  });

  it("keeps a draft per question and Class session", () => {
    expect(reflectionDraftField("s1", "feelings")).toBe("debrief-reflection:s1:feelings");
    expect(reflectionDraftField("s1", "feelings")).not.toBe(explanationDraftField("s1"));
  });

  it("words the step without praise, blame or exclamation marks", () => {
    const copy = nb.debrief.reflection;
    expect(copy.counter(2, 3)).toBe("Spørsmål 2 av 3");
    expect(copy.failed).toBe("Det ble ikke lagret. Prøv igjen.");
    for (const line of [copy.heading, copy.privacy, copy.next, copy.empty, copy.outOfOrder, copy.done, copy.loadFailed]) {
      expect(line).not.toMatch(/!|flink|bra jobbet|feil av/i);
    }
  });
});

describe("the own moments (Story 9.7)", () => {
  const answer = { text: "Svar.", length: 5, saved_at: "2026-11-21T12:00:00Z" };
  const question = (id: "feelings" | "evidence" | "structure", answered: boolean) => ({
    id,
    kind: id,
    prompt: "Hvorfor?",
    hint: null,
    answer: answered ? answer : null,
  });

  it("follow the reflection questions only once every one is answered", () => {
    expect(reflectionDone(undefined)).toBe(false);
    expect(reflectionDone({ version: 1, questions: [] })).toBe(false);
    expect(reflectionDone({ version: 1, questions: [question("feelings", true), question("evidence", false)] })).toBe(false);
    expect(reflectionDone({ version: 1, questions: [question("feelings", true), question("evidence", true)] })).toBe(true);
  });

  it("use the spine's labels and word the rest without praise, blame or exclamation marks", () => {
    const copy = nb.debrief.moments;
    expect([copy.saw, copy.reckoned, copy.later, copy.others(11)]).toEqual([
      "Dette så du",
      "Dette regnet du",
      "Dette kostet det senere",
      "Dette så de andre i Uke 11",
    ]);
    expect(copy.counter(1, 3)).toBe("Øyeblikk 1 av 3");
    expect(nb.debrief.aiPrefix).toBe("KI-generert, kan ta feil:");
    for (const line of [copy.heading, copy.mostlyAi, copy.mostlyAiChain, copy.previous, copy.next, copy.explanationNote, copy.loadFailed]) {
      expect(line).not.toMatch(/!|flink|bra jobbet|feil av/i);
    }
  });
});

describe("AI text in the Debrief (Story 9.14)", () => {
  it("marks AI text by `ai_generated` alone, with the text in «», and leaves code text as written", () => {
    expect(shownText({ text: "I Uke 3 bestilte du 12.", ai_generated: true, llm_call_id: "01a1" })).toBe(
      "KI-generert, kan ta feil: «I Uke 3 bestilte du 12.»",
    );
    expect(shownText({ text: "I Uke 3 bestilte du 12.", ai_generated: false, llm_call_id: null })).toBe(
      "I Uke 3 bestilte du 12.",
    );
    expect(nb.debrief.aiText("x").startsWith(nb.debrief.aiPrefix)).toBe(true);
    for (const line of [nb.debrief.aiNote, nb.debrief.moments.narration]) expect(line).not.toMatch(/!|flink|bra jobbet/i);
  });
});

describe("Kjedens regning in the Debrief (Story 9.8)", () => {
  const bill = (over: Partial<Bill> = {}): Bill => ({
    role: "wholesaler",
    total_cost: "2266.00",
    backorder_cost: "1365.00",
    backorder_share_percent: 60,
    backorder_costs_double: true,
    ai_held_cost: "0.00",
    ai_held_share_percent: 0,
    simulated: null,
    ...over,
  });
  const copy = nb.debrief.bill;

  it("words the restordre share as the spine does, with the reason only when backlog costs twice", () => {
    expect(backorderLine(bill(), copy)).toBe("Restordre er 60 % av kjedens regning, fordi den koster dobbelt.");
    expect(backorderLine(bill({ backorder_costs_double: false }), copy)).toBe("Restordre er 60 % av kjedens regning.");
    expect(backorderLine(bill({ backorder_share_percent: null }), copy)).toBeNull();
  });

  it("shows the AI line only when AI-held Weeks cost something", () => {
    expect(aiHeld(bill())).toBe(false);
    expect(aiHeld(bill({ ai_held_cost: "271.50", ai_held_share_percent: 12 }))).toBe(true);
    // A share that rounds to 0 % says nothing worth a line.
    expect(aiHeld(bill({ ai_held_cost: "3.50", ai_held_share_percent: 0 }))).toBe(false);
    expect(copy.aiShare(12, "271,50 kr")).toBe("12 % av kjedens regning, 271,50 kr, kom i uker der en KI-spiller hadde et sete.");
  });

  it("labels the simulated rows Simulert and never claims an answer", () => {
    expect([copy.simulated, copy.simulatedOwn, copy.simulatedAll, copy.simulatedNote]).toEqual([
      "Simulert, samme kunder",
      "Bare du teller på vei",
      "Alle fire teller på vei",
      "Simulert viser sammenhengen, ikke en fasit.",
    ]);
    for (const line of (Object.values(copy) as unknown[]).filter((v): v is string => typeof v === "string")) {
      expect(line).not.toMatch(/!|optimal|beste ordre/i);
    }
  });

  it("leads the staff to one page per Student", () => {
    expect(studentDebriefPath("s 1", "u/2")).toBe("/klasseokter/s%201/studenter/u%2F2/debrief");
  });
});

describe("the Debrief quiz (Story 9.9)", () => {
  const questions: Quiz["questions"] = [
    { id: "a", prompt: "A?", choices: [{ id: "x", text: "X" }, { id: "y", text: "Y" }] },
    { id: "b", prompt: "B?", choices: [{ id: "x", text: "X" }, { id: "z", text: "Z" }] },
  ];
  const quiz: Quiz = { version: 1, placeholder: true, attempts: 0, passed_at: null, questions, last: null };
  const attempt = (passed: boolean): QuizAttempt => ({
    number: 1,
    submitted_at: "2026-11-24T09:00:00Z",
    passed,
    correct: passed ? 2 : 1,
    asked: 2,
    results: [],
  });

  it("sends the choices in the order shown, and nothing while a question has none", () => {
    expect(quizAnswers(questions, { b: "z", a: "y" })).toEqual([
      { question_id: "a", choice_id: "y" },
      { question_id: "b", choice_id: "z" },
    ]);
    expect(quizAnswers(questions, { a: "y" })).toBeNull();
    expect(quizAnswers(questions, {})).toBeNull();
  });

  it("puts a stored attempt in as the last; a passing one leaves nothing to ask", () => {
    const failed = withAttempt(quiz, attempt(false));
    expect(failed).toMatchObject({ attempts: 1, passed_at: null, questions });
    expect(failed.last?.passed).toBe(false);
    const passed = withAttempt(quiz, attempt(true));
    expect(passed).toMatchObject({ attempts: 1, passed_at: "2026-11-24T09:00:00Z", questions: [] });
  });

  it("words the result and the pass without praise or an exclamation mark", () => {
    const copy = nb.debrief.quiz;
    expect(copy.result(2, 2, 3)).toBe("Forsøk 2: 2 av 3 riktige.");
    expect(copy.passed(1)).toBe("Alle svarene er riktige. Quizen er bestått på første forsøk.");
    expect(copy.passed(3)).toBe("Alle svarene er riktige. Quizen er bestått etter 3 forsøk.");
    for (const line of [copy.intro, copy.placeholder, copy.retryHint, copy.passed(2)]) expect(line).not.toContain("!");
  });
});

describe("the Klasseøkt's Debrief quiz block (Story 9.10)", () => {
  const quiz: SessionQuiz = {
    version: 1,
    placeholder: true,
    pinned: true,
    can_exclude: true,
    open: true,
    test_deadline: null,
    questions: [
      { id: "a", prompt: "A?", choices: [{ id: "x", text: "−13" }, { id: "y", text: "3" }], answer: "y", excluded: true },
      { id: "b", prompt: "B?", choices: [{ id: "x", text: "1" }], answer: "x", excluded: false },
    ],
  };

  it("lists the taken-out ids in the quiz's order and words the answer key by its choice", () => {
    expect(excludedIds(quiz)).toEqual(["a"]);
    expect(answerText(quiz.questions[0]!)).toBe("3");
    expect(nb.debrief.quizExclusions.answer(answerText(quiz.questions[0]!))).toBe("Riktig svar: 3");
  });

  it("words a Student's attempts for the staff, never with an exclamation mark", () => {
    const copy = nb.debrief.staffSummary;
    expect(copy.attempts(1)).toBe("1 forsøk.");
    expect(copy.attempts(3)).toBe("3 forsøk.");
    expect(copy.attempt(2, "lø. 21. nov. kl. 14:30", true)).toBe("Forsøk 2, lø. 21. nov. kl. 14:30: bestått");
    for (const line of Object.values(nb.debrief.quizExclusions)) {
      if (typeof line === "string") expect(line).not.toMatch(/!/);
    }
  });
});

describe("the Group debrief (Story 9.11)", () => {
  const words = nb.debriefEntry.group;
  const member = (name: string | null, you: boolean, sent: boolean, done = false): GroupMember => ({ name, you, sent, done });
  const group = (step: number, joined = true) => ({
    group: { step, joined, opener: false, step_opened_at: null, move_on_at: null, members: [] },
  });

  it("reaches every step in a Personal debrief, none before joining, then the shared pointer once sent", () => {
    expect(reach({ group: null }, false)).toBe(5);
    expect(reach(group(3, false), true)).toBe(0);
    expect(reach(group(3), false)).toBe(1);
    expect(reach(group(3), true)).toBe(3);
  });

  it("joins names with «og»", () => {
    expect(namesText([], "og")).toBe("");
    expect(namesText(["Ida"], "og")).toBe("Ida");
    expect(namesText(["Ida", "Mikkel", "Jonas"], "og")).toBe("Ida, Mikkel og Jonas");
  });

  it("names who has sent and who writes, the viewer first, never with a count in digits for four", () => {
    const members = [member("Jonas", false, false), member("Sara", true, true), member("Ida", false, true), member(null, false, false)];
    expect(lockedLine(members, words)).toBe(
      "Avsløringen er låst til alle fire har sendt. Du og Ida har sendt, Jonas og en som ikke lenger er i Klassen skriver.",
    );
    expect(lockedLine([member("Sara", true, true), member("Ida", false, true)], words)).toBeNull();
    expect(lockedLine([member("Sara", true, true), member("Ida", false, false)], words)).toBe(
      "Avsløringen er låst til begge har sendt. Du har sendt, Ida skriver.",
    );
  });

  it("waits for the others who have not finished", () => {
    expect(waitingFor([member("Sara", true, true, true), member("Ida", false, true, false), member("Jonas", false, true, true)], words)).toBe("Ida");
  });

  it("has no exclamation mark and never names customers before the reveal", () => {
    for (const line of [words.joinLead, words.timeGuide, words.behind(2), words.unlocked, words.alone, words.moveOnAt("14:05")]) {
      expect(line).not.toMatch(/!|kunde/i);
    }
  });
});

describe("going on alone (Story 9.12)", () => {
  const words = nb.debriefEntry.group;
  const alone = (reason: "left" | "dropout" | "fallback", from: number) => ({
    group: { step: 2, joined: false, opener: false, step_opened_at: null, move_on_at: null, members: [], alone: reason, alone_from: from },
  });

  it("reaches every step once the Student goes alone, whatever the shared pointer", () => {
    expect(reach(alone("left", 1), false)).toBe(5);
    expect(reach(alone("dropout", 2), true)).toBe(5);
  });

  it("puts the alone line under the step they were on, step 1 until they have sent, never past step 3", () => {
    expect(aloneAt({ alone_from: 2 }, true)).toBe(2);
    expect(aloneAt({ alone_from: 2 }, false)).toBe(1);
    expect(aloneAt({ alone_from: 4 }, true)).toBe(3);
    expect(aloneAt({ alone_from: null }, true)).toBe(1);
  });

  it("says why without an exclamation mark or customers before the reveal", () => {
    for (const line of [words.aloneLead, words.leaveConfirm, ...Object.values(words.aloneLine)]) {
      expect(line).not.toMatch(/!|kunde/i);
    }
  });
});

describe("the shared screen (Story 9.13)", () => {
  const week = (w: number, net: number) => ({
    week: w,
    order: 4,
    incoming_order: 4,
    inventory: Math.max(net, 0),
    backlog: Math.max(-net, 0),
    supply_line: 8,
    net_inventory: net,
  });
  const role = (r: "factory" | "retailer", holding: string, backorder: string, total: string, nets: number[]) => ({
    role: r,
    amplification: null,
    holding_cost: holding,
    backorder_cost: backorder,
    total_cost: total,
    weeks: nets.map((net, i) => week(i + 1, net)),
  });
  const chain: SharedChain = {
    last_week: 2,
    holding_cost: "6.000",
    backorder_cost: "4.000",
    total_cost: "10.000",
    roles: [role("factory", "6.000", "2.000", "8.000", [12, -3]), role("retailer", "0.000", "2.000", "2.000", [0])],
  };

  it("lists the cost per Role in the api's order, Fabrikk first, nobody's own, bars of the widest", () => {
    const model = sharedCostRows(chain, (r) => r, (v) => `kr ${v}`);
    expect(model.rows.map((r) => [r.role, r.own, r.holding, r.backorder, r.total])).toEqual([
      ["factory", false, "kr 6.000", "kr 2.000", "kr 8.000"],
      ["retailer", false, "kr 0.000", "kr 2.000", "kr 2.000"],
    ]);
    expect(model.rows.map((r) => r.bar)).toEqual([
      { holding: 0.75, backorder: 0.25 },
      { holding: 0, backorder: 0.25 },
    ]);
    expect(model.chain).toEqual({ holding: "kr 6.000", backorder: "kr 4.000", total: "kr 10.000" });
  });

  it("tables Netto lager by Uke, one column per Role, empty where a Role has no row", () => {
    expect(sharedNetRows(chain)).toEqual([
      { week: 1, nets: [12, 0] },
      { week: 2, nets: [-3, null] },
    ]);
  });

  it("marks no Role as the viewer's in the band and reads the chain Fabrikk first", () => {
    const input = chainBandInput(chain, 1, 600, 13);
    expect(input.nodes.map((n) => n.own)).toEqual([false, false]);
    expect(chainReading(chain, 1)).toMatch(/^Uke 1\. Fabrikk: lager 12, ordre 4\./);
    expect(sharedPath("a/b")).toBe("/delt-skjerm/a%2Fb");
  });
});

describe("follow-up questions (Story 9.15)", () => {
  const open: FollowUp = { state: "open", asked: [] };
  const answered: FollowUpAnswer = {
    outcome: "answered",
    question: "Hva skjedde i uke 3?",
    answer: { text: "Se på raden for Uke 3.", ai_generated: true, llm_call_id: "c" },
    asked_at: "2026-11-21T10:00:00Z",
  };

  it("adds a stored answer to the list and keeps it for no answer", () => {
    expect(withFollowUp(open, answered).asked).toEqual([answered]);
    const declined: FollowUpAnswer = { ...answered, outcome: "declined", answer: null };
    expect(withFollowUp(withFollowUp(open, answered), declined).asked.map((a) => a.outcome)).toEqual([
      "answered",
      "declined",
    ]);
    const none: FollowUpAnswer = { outcome: "unanswered", question: "x", answer: null, asked_at: null };
    expect(withFollowUp(open, none)).toBe(open);
  });

  it("words the wait in whole minutes, at least one", () => {
    expect(waitMinutes(30)).toBe(1);
    expect(waitMinutes(61)).toBe(2);
    expect(waitMinutes(600)).toBe(10);
    expect(waitMinutes(undefined)).toBe(1);
    expect(nb.debrief.followUp.rateLimited(1)).toMatch(/ett minutt/);
    expect(nb.debrief.followUp.rateLimited(4)).toMatch(/4 minutter/);
  });

  it("keeps the draft per Class session", () => {
    expect(followUpDraftField("s1")).toBe("debrief-follow-up:s1");
  });
});
