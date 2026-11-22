"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

/** The Klasseøkt's «Spørsmål og vekter» block (Story 11.1). */
export type QuestionSet = components["schemas"]["QuestionSetOut"];
export type QuestionItem = components["schemas"]["QuestionItemOut"];
export type QuestionSetBody = components["schemas"]["QuestionSetIn"];

/** Under `["class-sessions", id]`, so a `session:<id>` event reads it again. */
export const questionSetKey = (classSessionId: string) => ["class-sessions", classSessionId, "question-set"] as const;

export function useQuestionSet(classSessionId: string) {
  return useQuery({
    queryKey: questionSetKey(classSessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/question-set", { params: { path: { session_id: classSessionId } } }),
      ),
    retry: false,
  });
}

/** «Lagre vekter»: the whole selection. 422 `weights_not_100`, 409 `session_locked`, `class_archived`. */
export function saveQuestionSet(classSessionId: string, body: QuestionSetBody): Promise<QuestionSet> {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}/question-set", {
      params: { path: { session_id: classSessionId } },
      body,
    }),
  );
}

/** A weight as typed: a whole number from 0 to 100, the values the api accepts; null otherwise. */
export function parseWeight(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d{1,3}$/.test(trimmed)) return null;
  const value = Number(trimmed);
  return value <= 100 ? value : null;
}

/** The draft the block edits: each weight as typed, the items taken out, the Adapted total as typed. */
export type QuestionSetDraft = {
  /** The question set version the draft was made on: a draft of another version is dropped. */
  version: number;
  weights: Readonly<Record<string, string>>;
  excluded: ReadonlySet<string>;
  adapted: string;
};

export function draftOf(set: QuestionSet): QuestionSetDraft {
  return {
    version: set.version,
    weights: Object.fromEntries(set.items.map((item) => [item.id, String(item.weight)])),
    excluded: new Set(set.items.filter((item) => item.excluded).map((item) => item.id)),
    adapted: String(set.adapted.weight),
  };
}

/**
 * The live sum of a draft over the values the api accepts (a field it would refuse counts 0 and is
 * reported in `invalid`), the body to send when every field is valid, and whether a quantity item
 * is taken out. Display arithmetic only: the server judges the save.
 */
export function judgeDraft(set: QuestionSet, draft: QuestionSetDraft) {
  const invalid = new Set<string>();
  let sum = 0;
  const weights: Record<string, number> = {};
  for (const item of set.items) {
    const value = parseWeight(draft.weights[item.id] ?? "");
    if (value === null) {
      if (!draft.excluded.has(item.id)) invalid.add(item.id);
      weights[item.id] = item.weight;
      continue;
    }
    weights[item.id] = value;
    if (!draft.excluded.has(item.id)) sum += value;
  }
  const adapted = parseWeight(draft.adapted);
  if (adapted === null) invalid.add("adapted");
  else sum += adapted;
  const quantityOut = set.items.some((item) => item.quantity && draft.excluded.has(item.id));
  const body: QuestionSetBody | null =
    invalid.size === 0 && adapted !== null
      ? { weights, excluded: set.items.filter((i) => draft.excluded.has(i.id)).map((i) => i.id), adapted_weight: adapted }
      : null;
  return { sum, invalid, quantityOut, body };
}

/** The Klasseøkt's «Sensorveiledning» block (Story 11.2). */
export type ScoringGuide = components["schemas"]["ScoringGuideOut"];
export type GuideQuestion = components["schemas"]["GuideQuestionOut"];
export type ScoringGuideBody = components["schemas"]["ScoringGuideIn"];

/** The longest guide text of one question the api takes. */
export const GUIDE_TEXT_MAX = 4000;

/** Under `["class-sessions", id]`, so a `session:<id>` event reads it again. */
export const scoringGuideKey = (classSessionId: string) => ["class-sessions", classSessionId, "scoring-guide"] as const;

export function useScoringGuide(classSessionId: string) {
  return useQuery({
    queryKey: scoringGuideKey(classSessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/scoring-guide", { params: { path: { session_id: classSessionId } } }),
      ),
    retry: false,
  });
}

/** «Lagre sensorveiledning»: the changed texts only. 409 `scoring_guide_locked`, `class_archived`; 422 `validation_error`. */
export function saveScoringGuide(classSessionId: string, body: ScoringGuideBody): Promise<ScoringGuide> {
  return request(() =>
    api.PUT("/api/class-sessions/{session_id}/scoring-guide", {
      params: { path: { session_id: classSessionId } },
      body,
    }),
  );
}

/** What is wrong with a guide text as typed, for the reason under its Tekstfelt; null when the api takes it. */
export function guideTextProblem(text: string): "empty" | "tooLong" | null {
  if (text.trim() === "") return "empty";
  if (text.length > GUIDE_TEXT_MAX) return "tooLong";
  return null;
}

/**
 * The body «Lagre sensorveiledning» sends: only the texts the Lecturer touched that differ from the
 * guide in force, so a save never writes back another owner's text it merely showed. Null when
 * nothing differs or a touched text is one the api refuses.
 */
export function guideBody(guide: ScoringGuide, draft: Readonly<Record<string, string>>): ScoringGuideBody | null {
  const guides: Record<string, string> = {};
  for (const question of guide.questions) {
    const text = draft[question.id];
    if (text === undefined || text === question.guide) continue;
    if (guideTextProblem(text) !== null) return null;
    guides[question.id] = text;
  }
  return Object.keys(guides).length > 0 ? { guides } : null;
}
