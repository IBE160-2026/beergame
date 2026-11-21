"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Student's Debrief session (Story 9.2): its id (the `debrief:<id>` topic), the game it
 * reviews and the step pointer, 1 to 5. */
export type Debrief = components["schemas"]["DebriefOut"];

/** The prefix of every Debrief query: the `user` and `debrief` topics invalidate it. */
export const debriefsKey = ["debriefs"] as const;
export const myDebriefKey = (classSessionId: string) => [...debriefsKey, "mine", classSessionId] as const;

/** The Debrief's five steps (EXPERIENCE.md → Debrief sequence). */
export const DEBRIEF_STEPS = 5;

/**
 * Opens the Student's Debrief in the Class session and reads it: the api creates the Debrief
 * session at step 1 the first time and answers the same session after that, so the page, «Gå til
 * Debrief» and Stegene share one way in (FR-42). 403 `debrief_not_open`, `debrief_held` or
 * `forbidden` before it may open.
 */
export function useMyDebrief(classSessionId: string) {
  return useQuery({
    queryKey: myDebriefKey(classSessionId),
    queryFn: () =>
      request(() =>
        api.POST("/api/me/class-sessions/{session_id}/debrief", { params: { path: { session_id: classSessionId } } }),
      ),
    retry: false,
  });
}

/** A Group debrief's shared step pointer (Story 9.11): null on a Personal debrief. */
export type Group = components["schemas"]["GroupOut"];
export type GroupMember = components["schemas"]["GroupMemberOut"];

/** The step from which each Student works alone: the pointer stops there (FR-43). */
export const INDIVIDUAL_STEP = 4;

/**
 * How far the Student's page reaches (Story 9.11), from the api's answer alone: a Personal debrief
 * every step the Student's own progress opens (5); a Group debrief the Student has not joined
 * none (only the way to join, 0); a joined Student step 1 until their Explanation is sent, then
 * the shared pointer (the api refuses the steps after it, 403 `step_locked`). A Student who goes on
 * alone (Story 9.12: left, dropped out or the 48-hour fallback) reads it as a Personal debrief.
 */
export function reach(debrief: Pick<Debrief, "group">, sent: boolean): number {
  const group = debrief.group;
  if (!group || group.alone) return DEBRIEF_STEPS;
  if (!group.joined) return 0;
  return sent ? group.step : 1;
}

/** «Ida», «Ida og Mikkel», «Ida, Mikkel og Jonas». */
export function namesText(names: readonly string[], and: string): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} ${and} ${names[names.length - 1]}`;
}

/** A joined Student as the lines name them: «du» for the viewer, the Roster name, or a stand-in
 * for one no longer in the Class. */
function memberName(member: GroupMember, words: { you: string; someone: string }): string {
  if (member.you) return words.you;
  return member.name ?? words.someone;
}

function capitalised(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** «Avsløringen er låst til begge har sendt. Du har sendt, Jonas skriver.»: shown to a joined
 * Student who has sent while another writes; null when nobody is left writing. The viewer first. */
export function lockedLine(
  members: readonly GroupMember[],
  words: {
    you: string;
    someone: string;
    and: string;
    everyone: (count: number) => string;
    locked: (everyone: string, sent: string, writing: string) => string;
  },
): string | null {
  const ordered = [...members].sort((a, b) => Number(b.you) - Number(a.you));
  const sent = ordered.filter((m) => m.sent).map((m) => memberName(m, words));
  const writing = ordered.filter((m) => !m.sent).map((m) => memberName(m, words));
  if (sent.length === 0 || writing.length === 0) return null;
  return words.locked(words.everyone(members.length), capitalised(namesText(sent, words.and)), namesText(writing, words.and));
}

/** The joined Students who have not finished the shared step, by name, for «Venter på …». */
export function waitingFor(members: readonly GroupMember[], words: { you: string; someone: string; and: string }): string {
  return namesText(
    members.filter((m) => !m.done && !m.you).map((m) => memberName(m, words)),
    words.and,
  );
}

/** «Bli med»: joins the Group debrief of the Student's game (409 `not_group` on a Personal one). */
export function joinDebrief(debriefId: string): Promise<Debrief> {
  return request(() => api.POST("/api/debriefs/{debrief_id}/join", { params: { path: { debrief_id: debriefId } } }));
}

/** «Forlat gruppen» / «Ta en Personlig debrief» (Story 9.12): the Student goes on alone, final;
 * 409 `not_group` on a Personal debrief. */
export function leaveDebrief(debriefId: string): Promise<Debrief> {
  return request(() => api.POST("/api/debriefs/{debrief_id}/leave", { params: { path: { debrief_id: debriefId } } }));
}

/** Where the alone line stands (Story 9.12): under the shared step the Student was on, or step 1
 * while their Explanation is not sent; at most step 3, the last shared one. */
export function aloneAt(group: Pick<Group, "alone_from">, sent: boolean): number {
  const from = Math.min(group.alone_from ?? 1, INDIVIDUAL_STEP - 1);
  return sent ? from : 1;
}

/** «Ferdig med steget» on shared step 2 or 3. */
export function completeStep(debriefId: string, step: number): Promise<Debrief> {
  return request(() =>
    api.POST("/api/debriefs/{debrief_id}/steps/{step}/done", { params: { path: { debrief_id: debriefId, step } } }),
  );
}

/** «Gå videre for alle», the opener's: 409 `too_early` with `fields.available_at` before the wait. */
export function moveOn(debriefId: string): Promise<Debrief> {
  return request(() => api.POST("/api/debriefs/{debrief_id}/move-on", { params: { path: { debrief_id: debriefId } } }));
}

/** Where the Debrief page stands, from the api's answer or refusal: the web app decides nothing. */
export type DebriefView = "open" | "notOpen" | "held" | "denied" | "other";

export function debriefView(data: Debrief | undefined, code: string | null): DebriefView {
  if (data) return "open";
  if (code === "debrief_not_open") return "notOpen";
  if (code === "debrief_held") return "held";
  if (code === "forbidden") return "denied";
  return "other";
}

/** The Student's own Netto lager per Uke (Story 9.3, step 1). */
export type NetInventory = components["schemas"]["NetInventoryOut"];
/** A sent Explanation: the text as typed, its length and when it was saved. */
export type Explanation = components["schemas"]["ExplanationOut"];

export const netInventoryKey = (debriefId: string) => [...debriefsKey, debriefId, "net-inventory"] as const;
export const explanationKey = (debriefId: string) => [...debriefsKey, debriefId, "explanation"] as const;

/** «Ditt netto lager, hele spillet»: the Student's own Seat only, every Uke (no demand). */
export function useNetInventory(debriefId: string) {
  return useQuery({
    queryKey: netInventoryKey(debriefId),
    queryFn: () =>
      request(() => api.GET("/api/debriefs/{debrief_id}/net-inventory", { params: { path: { debrief_id: debriefId } } })),
    retry: false,
  });
}

/** The Student's own Explanation, `explanation` null before it is sent. */
export function useMyExplanation(debriefId: string) {
  return useQuery({
    queryKey: explanationKey(debriefId),
    queryFn: () =>
      request(() => api.GET("/api/debriefs/{debrief_id}/explanation", { params: { path: { debrief_id: debriefId } } })),
    retry: false,
  });
}

/** «Send Forklaring»: stores the Explanation once (FR-41). Nothing here sends on its own. */
export function sendExplanation(debriefId: string, text: string): Promise<Explanation> {
  return request(() =>
    api.POST("/api/debriefs/{debrief_id}/explanation", {
      params: { path: { debrief_id: debriefId } },
      body: { text },
    }),
  );
}

/** The draft field of the Explanation in a Class session (`lib/drafts.ts`). */
export const explanationDraftField = (classSessionId: string) => `debrief-explanation:${classSessionId}`;

/** Whether typed text may be sent: more than white space (the api refuses the rest). */
export function hasText(text: string): boolean {
  return text.trim() !== "";
}

/** A Debrief step after step 1 (Story 9.3): 403 `explanation_required` until the Explanation is
 * saved. Step 2 carries `reveal` (Story 9.4). */
export type DebriefStep = components["schemas"]["DebriefStepOut"];
/** Step 2, the reveal of customer demand: the heading from the api and Kundene, Ordre inn and Din
 * ordre per Uke of the Student's own Seat. */
export type Reveal = components["schemas"]["RevealOut"];
export type RevealWeek = components["schemas"]["RevealWeekOut"];
/** Step 3, the whole chain (Story 9.5): every Role, Fabrikk first, with its Orders and Week states
 * per Uke, Forsterkning and the first large Order from the stored facts. */
export type Chain = components["schemas"]["ChainOut"];
export type ChainRole = components["schemas"]["ChainRoleOut"];
export type ChainWeek = components["schemas"]["ChainWeekOut"];
/** Step 4, the Student's own moments (Story 9.7): every sentence rendered by code from the
 * stored facts, the other Roles' numbers and the Seat's Week as it saw it, per moment. */
export type Moments = components["schemas"]["MomentsOut"];
export type Moment = components["schemas"]["MomentOut"];
/** Text the Debrief shows as written: `ai_generated` alone decides the «KI-generert» prefix. */
export type RenderedText = components["schemas"]["RenderedTextOut"];

export const debriefStepKey = (debriefId: string, step: number) => [...debriefsKey, debriefId, "steps", step] as const;

/** A step's content, read once the Explanation is saved (`enabled`): the api checks the gate. */
export function useDebriefStep(debriefId: string, step: number, enabled: boolean) {
  return useQuery({
    queryKey: debriefStepKey(debriefId, step),
    queryFn: () =>
      request(() =>
        api.GET("/api/debriefs/{debrief_id}/steps/{step}", { params: { path: { debrief_id: debriefId, step } } }),
      ),
    enabled,
    retry: false,
  });
}

/** The Role whose Orders reached a Seat: the next one down the chain toward the customers
 * (EXPERIENCE.md → Chain convention). None for the Detaljist, who saw the customers. */
export function downstreamRole(role: Debrief["role"]): Debrief["role"] | null {
  const chain = ["factory", "distributor", "wholesaler", "retailer"] as const;
  const at = chain.indexOf(role);
  return at >= 0 && at < chain.length - 1 ? chain[at + 1]! : null;
}

/** The reflection questions between steps 3 and 4 (Story 9.6, FR-45): the pinned version's
 * questions, feelings, then evidence, then structure, each with the Student's own answer. */
export type Reflection = components["schemas"]["ReflectionOut"];
export type ReflectionQuestion = components["schemas"]["ReflectionQuestionOut"];

export const reflectionKey = (debriefId: string) => [...debriefsKey, debriefId, "reflection"] as const;

/** The reflection questions, read once the Explanation is saved (`enabled`): the api checks the
 * gate. */
export function useMyReflection(debriefId: string, enabled: boolean) {
  return useQuery({
    queryKey: reflectionKey(debriefId),
    queryFn: () =>
      request(() => api.GET("/api/debriefs/{debrief_id}/reflection", { params: { path: { debrief_id: debriefId } } })),
    enabled,
    retry: false,
  });
}

/** «Fortsett»: stores the answer to one question once (FR-45). Nothing here sends on its own. */
export function answerReflection(debriefId: string, questionId: string, text: string): Promise<ReflectionQuestion> {
  return request(() =>
    api.POST("/api/debriefs/{debrief_id}/reflection/{question_id}", {
      params: { path: { debrief_id: debriefId, question_id: questionId } },
      body: { text },
    }),
  );
}

/** The draft field of one reflection answer in a Class session (`lib/drafts.ts`). */
export const reflectionDraftField = (classSessionId: string, questionId: string) =>
  `debrief-reflection:${classSessionId}:${questionId}`;

/** The question to answer now: the first without an answer; null once all are answered. The api
 * takes only this one (409 `reflection_out_of_order`). */
export function currentQuestion(reflection: Reflection): ReflectionQuestion | null {
  return reflection.questions.find((q) => q.answer === null) ?? null;
}

/** The reflection with one question's stored answer put in, as the api answered it. */
export function withAnswer(reflection: Reflection, answered: ReflectionQuestion): Reflection {
  return { ...reflection, questions: reflection.questions.map((q) => (q.id === answered.id ? answered : q)) };
}

/** Whether the reflection questions are all answered, so step 4 follows (Story 9.7). */
export function reflectionDone(reflection: Reflection | undefined): boolean {
  return Boolean(reflection && reflection.questions.length > 0 && currentQuestion(reflection) === null);
}

/** Step 4's lines under Kjedens regning (Story 9.8): the restordre share, the AI-held share and
 * «Simulert, samme kunder», every number from the stored facts set. */
export type Bill = components["schemas"]["BillOut"];
export type SimulatedRow = components["schemas"]["SimulatedRowOut"];
/** A finished Debrief (Story 9.8): the key moments, the reflection answers and the time. */
export type Summary = components["schemas"]["SummaryOut"];
export type MySummary = components["schemas"]["MySummaryOut"];
/** A Student's Explanation and Debrief summary for the Class's staff. */
export type StaffSummary = components["schemas"]["StaffSummaryOut"];

export const summaryKey = (debriefId: string) => [...debriefsKey, debriefId, "summary"] as const;

/** The Student's own Debrief summary, `summary` null until «Fullfør Debriefen». */
export function useMySummary(debriefId: string, enabled: boolean) {
  return useQuery({
    queryKey: summaryKey(debriefId),
    queryFn: () =>
      request(() => api.GET("/api/debriefs/{debrief_id}/summary", { params: { path: { debrief_id: debriefId } } })),
    enabled,
    retry: false,
  });
}

/** «Fullfør Debriefen»: stores the summary once and records the `debrief` step (FR-47). A
 * finished Debrief answers its stored summary unchanged. */
export function finishDebrief(debriefId: string): Promise<MySummary> {
  return request(() => api.POST("/api/debriefs/{debrief_id}/finish", { params: { path: { debrief_id: debriefId } } }));
}

export const staffSummaryKey = (classSessionId: string, studentId: string) =>
  ["class-sessions", classSessionId, "students", studentId, "debrief-summary"] as const;

/** A Student's Explanation and Debrief summary, for the Class's owners and Assistant lecturers;
 * 403 `forbidden` for everyone else. */
export function useStaffSummary(classSessionId: string, studentId: string) {
  return useQuery({
    queryKey: staffSummaryKey(classSessionId, studentId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/students/{student_id}/debrief-summary", {
          params: { path: { session_id: classSessionId, student_id: studentId } },
        }),
      ),
    retry: false,
  });
}

/** The bill's restordre line: «Restordre er 60 % av kjedens regning, fordi den koster dobbelt.»,
 * without the reason when backlog does not cost twice inventory; null when the chain cost
 * nothing. */
export function backorderLine(bill: Bill, copy: { share: (p: number) => string; shareDouble: (p: number) => string }): string | null {
  if (bill.backorder_share_percent === null) return null;
  return bill.backorder_costs_double ? copy.shareDouble(bill.backorder_share_percent) : copy.share(bill.backorder_share_percent);
}

/** Whether AI players held Seats in Weeks that cost something, at least half a percent of the
 * chain's cost (so the line never reads «0 %»): only then the AI line shows. */
export function aiHeld(bill: Bill): boolean {
  return Number(bill.ai_held_cost) > 0 && (bill.ai_held_share_percent ?? 0) > 0;
}

/** Step 5, the Debrief quiz (Story 9.9, FR-46): the pinned version, the next attempt's questions
 * (no answer key; none once passed) and the latest attempt's result. */
export type Quiz = components["schemas"]["QuizOut"];
export type QuizQuestion = components["schemas"]["QuizQuestionOut"];
export type QuizAttempt = components["schemas"]["QuizAttemptOut"];
export type QuizResult = components["schemas"]["QuizResultOut"];

export const quizKey = (debriefId: string) => [...debriefsKey, debriefId, "quiz"] as const;

/** The Debrief quiz, read once the Debrief is finished (`enabled`): the api checks the gate (403
 * `debrief_required`). */
export function useMyQuiz(debriefId: string, enabled: boolean) {
  return useQuery({
    queryKey: quizKey(debriefId),
    queryFn: () => request(() => api.GET("/api/debriefs/{debrief_id}/quiz", { params: { path: { debrief_id: debriefId } } })),
    enabled,
    retry: false,
  });
}

/** One attempt: the choices in the order shown. The api scores it by the answer key (FR-46);
 * nothing here judges an answer. */
export function submitQuiz(debriefId: string, answers: readonly { question_id: string; choice_id: string }[]): Promise<QuizAttempt> {
  return request(() =>
    api.POST("/api/debriefs/{debrief_id}/quiz/attempts", {
      params: { path: { debrief_id: debriefId } },
      body: { answers: [...answers] },
    }),
  );
}

/** The answers to send, in the order the questions are shown; null while a question has no
 * choice (the api would refuse it). */
export function quizAnswers(
  questions: readonly QuizQuestion[],
  chosen: Readonly<Record<string, string>>,
): { question_id: string; choice_id: string }[] | null {
  const answers = questions.map((q) => ({ question_id: q.id, choice_id: chosen[q.id] ?? "" }));
  return answers.every((a) => a.choice_id !== "") ? answers : null;
}

/** The quiz as it stands once `attempt` is stored: the attempt is the last, and once it passed
 * there is nothing left to ask. The next attempt's questions come with the refetch. */
export function withAttempt(quiz: Quiz, attempt: QuizAttempt): Quiz {
  return {
    ...quiz,
    attempts: attempt.number,
    last: attempt,
    passed_at: attempt.passed ? attempt.submitted_at : quiz.passed_at,
    questions: attempt.passed ? [] : quiz.questions,
  };
}

/** The Klasseøkt's «Debrief-quiz» block (Story 9.10, FR-46): the Class session's quiz with its
 * answer keys and which questions are taken out, for its owners and Assistant lecturers. */
export type SessionQuiz = components["schemas"]["StaffQuizOut"];
export type SessionQuizQuestion = components["schemas"]["StaffQuizQuestionOut"];

/** Under the `["class-sessions", id]` prefix, so the `session` topic reads it again. */
export const sessionQuizKey = (classSessionId: string) => ["class-sessions", classSessionId, "debrief-quiz"] as const;

export function useSessionQuiz(classSessionId: string) {
  return useQuery({
    queryKey: sessionQuizKey(classSessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/debrief-quiz", { params: { path: { session_id: classSessionId } } }),
      ),
    retry: false,
  });
}

/** «Lagre quizvalg»: the whole set of questions to take out; the api stores, audits and tells the
 * Students it concerns. 409 `last_question`, `test_deadline_passed`, `class_archived`. */
export function saveQuizExclusions(classSessionId: string, excluded: readonly string[]): Promise<SessionQuiz> {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}/debrief-quiz/exclusions", {
      params: { path: { session_id: classSessionId } },
      body: { excluded: [...excluded] },
    }),
  );
}

/** The ids taken out in `quiz`, in the quiz's order. */
export function excludedIds(quiz: SessionQuiz): string[] {
  return quiz.questions.filter((q) => q.excluded).map((q) => q.id);
}

/** The text of a question's right choice (its answer key). */
export function answerText(question: SessionQuizQuestion): string {
  return question.choices.find((c) => c.id === question.answer)?.text ?? question.answer;
}
