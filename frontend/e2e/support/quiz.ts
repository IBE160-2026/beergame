import type { Page, Route } from "@playwright/test";

/** Stand-in answers of the Debrief quiz (Story 9.9) with the api's shapes: three placeholder
 * questions, and a stub that scores an attempt by this answer key as the api does, so a wrong
 * attempt, a retry (the order reshuffled) and a pass can be driven from the page. The api's
 * scoring, storage and refusals are `backend/tests/debrief/test_quiz.py`. */
export const QUESTIONS = [
  {
    id: "posisjon",
    prompt: "Du har 0 på lager, 13 i restordre og 16 på vei. Hva er posisjonen din?",
    choices: [
      { id: "netto", text: "−13" },
      { id: "posisjon", text: "3" },
      { id: "sum", text: "29" },
    ],
  },
  {
    id: "forsinkelse",
    prompt: "Du øker ordren din i én uke. Når kommer varene fram?",
    choices: [
      { id: "samme-uke", text: "Samme uke" },
      { id: "uka-etter", text: "Uka etter" },
      { id: "flere-uker", text: "Først etter flere uker" },
    ],
  },
  {
    id: "forsterkning",
    prompt: "Hvor i kjeden svinger ordrene mest?",
    choices: [
      { id: "detaljist", text: "Hos Detaljisten" },
      { id: "like-mye", text: "Like mye i alle ledd" },
      { id: "fabrikk", text: "Hos Fabrikken" },
    ],
  },
];

export const KEY: Record<string, string> = { posisjon: "posisjon", forsinkelse: "flere-uker", forsterkning: "fabrikk" };

export const EXPLANATION =
  "Posisjonen er lager − restordre + på vei: 0 − 13 + 16 = 3. −13 er netto lager, uten det som er på vei. Ditt første øyeblikk var Uke 11. Det står i kolonne 11 i din egen tabell.";

type Attempt = {
  number: number;
  submitted_at: string;
  passed: boolean;
  correct: number;
  asked: number;
  results: object[];
};

/** The quiz endpoints of `debriefId`: GET answers what is stored so far; POST scores and stores,
 * or answers `refuse` (an error code) with 409. Questions of a retry come in reverse order. */
export async function stubQuiz(page: Page, debriefId: string, { refuse = null as string | null } = {}) {
  const attempts: Attempt[] = [];
  const posts: { question_id: string; choice_id: string }[][] = [];
  const quiz = () => {
    const last = attempts.at(-1) ?? null;
    const passed = Boolean(last?.passed);
    return {
      version: 1,
      placeholder: true,
      attempts: attempts.length,
      passed_at: passed ? last!.submitted_at : null,
      questions: passed ? [] : attempts.length === 0 ? QUESTIONS : [...QUESTIONS].reverse(),
      last,
    };
  };
  await page.route(`**/api/debriefs/${debriefId}/quiz`, (route) => route.fulfill({ json: quiz() }));
  await page.route(`**/api/debriefs/${debriefId}/quiz/attempts`, (route: Route) => {
    const answers = (route.request().postDataJSON() as { answers: { question_id: string; choice_id: string }[] }).answers;
    posts.push(answers);
    if (refuse) return route.fulfill({ status: 409, json: { error: { code: refuse, message: "x" } } });
    const results = answers.map(({ question_id, choice_id }) => {
      const question = QUESTIONS.find((q) => q.id === question_id)!;
      const correct = KEY[question_id] === choice_id;
      return {
        question_id,
        prompt: question.prompt,
        choices: question.choices,
        chosen: choice_id,
        right_choice: KEY[question_id],
        correct,
        explanation: correct
          ? null
          : { text: question_id === "posisjon" ? EXPLANATION : "Forklaringen.", ai_generated: false, llm_call_id: null },
      };
    });
    const correct = results.filter((r) => r.correct).length;
    const attempt = {
      number: attempts.length + 1,
      submitted_at: `2026-11-21T14:0${attempts.length + 1}:00Z`,
      passed: correct === results.length,
      correct,
      asked: results.length,
      results,
    };
    attempts.push(attempt);
    return route.fulfill({ status: 201, json: attempt });
  });
  return { posts };
}
