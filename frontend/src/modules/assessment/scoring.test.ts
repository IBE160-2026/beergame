import { describe, expect, it } from "vitest";

import { ApiRequestError } from "@/lib/api/client";

import { aiText, answerLabel, ownText, progressText, scaleOptions, scorerError, submitError, testLine, typeText } from "./scoring";
import type { ScoringEntry, ScoringItem } from "./scoring-api";

const SCALE = [0, 1, 2, 3, 4].map((step) => ({ step, label: ["mangler", "svakt", "delvis", "godt", "svært godt"][step] }));

function item(overrides: Partial<ScoringItem> = {}): ScoringItem {
  return {
    test: { id: "t", name: "Kontrolltest høst", test_deadline: "2026-12-12T22:59:00Z", open: true },
    ref: "a",
    number: 3,
    type: "long",
    question: "Hvorfor svinger ordrene?",
    answer: "Forsinkelsen.",
    facts: [],
    guide_title: "Forsinkelse",
    guide_text: "Se etter årsak.",
    criteria: [],
    scale: SCALE,
    can_score: true,
    own_score: null,
    ai: null,
    ...overrides,
  };
}

const entry = (scored: boolean): ScoringEntry => ({ ref: "x", number: 1, type: "long", question: "q", scored });

describe("blind scoring (Story 12.9)", () => {
  it("names an answer by a neutral number and counts the reader's progress in text", () => {
    expect(answerLabel(12)).toBe("Svar 12");
    expect(progressText([entry(true), entry(false), entry(false)])).toBe("1 av 3 vurdert");
    expect(typeText("adapted")).toBe("Tilpasset oppgave");
  });

  it("says when a closed Control test opens, and links an open one by name", () => {
    expect(testLine(item().test)).toBe("Vurder svarene i Kontrolltest høst");
    expect(testLine({ ...item().test, open: false })).toBe("Åpner etter testfristen 12. des. 2026 kl. 23:59.");
  });

  it("offers the five steps with their labels", () => {
    expect(scaleOptions(item()).map((o) => o.label)).toEqual(["0: mangler", "1: svakt", "2: delvis", "3: godt", "4: svært godt"]);
  });

  it("keeps the AI's step hidden until the reader's own score is saved", () => {
    expect(ownText(item())).toBeNull();
    expect(aiText(item({ ai: { step: 2, label: "delvis" } }))).toBe("KI-vurderingen vises når din vurdering er lagret.");
    const scored = item({ own_score: { score: 3, submitted_at: "2026-12-13T08:00:00Z" }, ai: { step: 2, label: "delvis" } });
    expect(ownText(scored)).toBe("Din vurdering: 3 av 4, godt.");
    expect(aiText(scored)).toBe("KI-vurderingen: 2 av 4, delvis.");
    expect(aiText({ ...scored, ai: null })).toBe("KI-vurderingen av dette svaret er ikke klar ennå.");
  });

  it("words a rejected second score and a refused scorer", () => {
    expect(submitError(new ApiRequestError(409, "human_score_exists"))).toBe(
      "Du har allerede vurdert dette svaret. Vurderingen kan ikke endres.",
    );
    expect(submitError(new ApiRequestError(500, "internal_error"))).toBe("Det ble ikke lagret. Prøv igjen.");
    expect(scorerError(new ApiRequestError(422, "invalid_request", { email: "test_student" }))).toBe(
      "En teststudent kan ikke være sensor.",
    );
    expect(scorerError(new ApiRequestError(422, "invalid_request", { email: "unknown" }))).toBe(
      "Ingen aktiv bruker har denne adressen.",
    );
    expect(scorerError(new ApiRequestError(0, "network_error"))).toBe("Sensoren ble ikke utnevnt. Prøv igjen.");
  });
});
