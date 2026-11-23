import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import {
  type Completion,
  completionRows,
  debriefLines,
  duration,
  gameLines,
  makeupLines,
  participationLines,
  quizLines,
  replayLine,
  requirementLine,
  shareLines,
  testLines,
} from "./record";

const copy = nb.reports.completion;
const AT = "2026-12-12T09:00:00Z";

function completion(changes: Partial<Completion> = {}): Completion {
  const steps = (["class_game", "debrief", "quiz_passed", "replay", "test_submitted"] as const).map((step) => ({
    step,
    recorded: true,
    recorded_at: AT,
    done: true,
    corrected: false,
  }));
  return {
    obligatory: true,
    requirement_met: true,
    required_share: 80,
    adjusted: false,
    ordered_share: 70,
    playout_share: 20,
    steps,
    ...changes,
  };
}

describe("the «Fullføring» block (Story 13.2, UX-DR54)", () => {
  it("says each status in text and names the steps in order", () => {
    const rows = completionRows(
      completion({
        steps: completion().steps.map((s) => (s.step === "replay" ? { ...s, recorded: false, recorded_at: null, done: false } : s)),
      }),
    );
    expect(rows.map((r) => r.name)).toEqual(["Klassespill", "Debrief", "Debrief-quiz", "Replay", "Individuell test"]);
    expect(rows.map((r) => r.status)).toEqual(["gjort", "gjort", "gjort", "ikke gjort", "gjort"]);
    expect(rows[3]!.lines).toEqual([]);
    expect(rows[1]!.lines).toEqual(["Registrert lø. 12. des."]);
  });

  it("reads a corrected step as «Gjort, rettet av …» with the reason, and no not-counted line (Story 13.3)", () => {
    const rows = completionRows(
      completion({
        steps: completion().steps.map((s) =>
          s.step === "debrief"
            ? { ...s, done: true, corrected: true, correction: { done: true, reason: "Syk i uke 3.", at: AT, by: "Bård Pettersen" } }
            : s.step === "replay"
              ? { ...s, done: false, corrected: true, correction: { done: false, reason: "Ikke fullført.", at: AT, by: null } }
              : s,
        ),
      }),
    );
    expect(rows[1]).toMatchObject({ status: "Gjort, rettet av Bård Pettersen 12. des.", corrected: true, reason: "Syk i uke 3." });
    expect(rows[1]!.lines).toEqual(["Registrert lø. 12. des."]);
    expect(rows[3]).toMatchObject({ status: "Ikke gjort, rettet av en faglærer 12. des.", reason: "Ikke fullført." });
    expect(rows[0]).toMatchObject({ status: "gjort", corrected: false, reason: null });
  });

  it("puts the share lines on the Klassespill row, the requirement only when obligatory", () => {
    expect(shareLines(completion())).toEqual([
      "Bestilte i 70 % av ukene. Kravet er 80 %.",
      "20 % av ukene ble spilt i utspillingen ved Spillfristen.",
    ]);
    expect(shareLines(completion({ obligatory: false, requirement_met: null, playout_share: 0 }))).toEqual([
      "Bestilte i 70 % av ukene.",
    ]);
    expect(shareLines(completion({ adjusted: true, required_share: 60 }))[0]).toBe(
      "Bestilte i 70 % av ukene. Kravet er 60 % (tilrettelagt).",
    );
    expect(shareLines(completion({ ordered_share: null }))).toEqual([]);
    expect(completionRows(completion())[0]!.lines).toContain("Bestilte i 70 % av ukene. Kravet er 80 %.");
  });

  it("says why a recorded step does not count, unless a correction decided it", () => {
    const short = completion({
      steps: completion().steps.map((s) => (s.step === "debrief" ? { ...s, done: false } : s)),
    });
    expect(completionRows(short)[1]!.lines).toContain(copy.notCounted.debrief);
    const corrected = completion({
      steps: completion().steps.map((s) => (s.step === "debrief" ? { ...s, done: false, corrected: true } : s)),
    });
    expect(completionRows(corrected)[1]!.lines).not.toContain(copy.notCounted.debrief);
  });

  it("states the requirement line only for an obligatory Class session", () => {
    expect(requirementLine(completion())).toBe("Kravet er oppfylt.");
    expect(requirementLine(completion({ requirement_met: false }))).toBe("Kravet er ikke oppfylt.");
    expect(requirementLine(completion({ obligatory: false, requirement_met: null }))).toBeNull();
  });
});

describe("the Oppfølgingsspill on the Klassespill row (Story 13.4)", () => {
  it("names the game the share comes from once the Student has one", () => {
    expect(shareLines(completion({ share_game: "makeup", ordered_share: 100, playout_share: 0 }))).toEqual([
      "Bestilte i 100 % av ukene i Oppfølgingsspillet. Kravet er 80 %.",
    ]);
    expect(shareLines(completion({ share_game: "class" }))[0]).toBe(
      "Bestilte i 70 % av ukene i Klassespillet. Kravet er 80 %.",
    );
  });

  it("says when it was given, until when it is open and where it stands", () => {
    expect(makeupLines(null)).toBeNull();
    const given = { game_id: "g", given_at: AT, open_until: "2026-12-18T22:59:00Z", state: "ready" as const };
    expect(makeupLines(given)).toEqual({
      given: "Oppfølgingsspill gitt 12. des. Åpent til fr. 18. des.",
      state: "Ikke startet ennå.",
    });
    expect(makeupLines({ ...given, state: "ended", open_until: null })).toEqual({
      given: "Oppfølgingsspill gitt 12. des.",
      state: "Stengt ved Testfristen før siste uke.",
    });
  });

  it("states the consequence in the spine's words, with a full stop after a month that has none", () => {
    expect(copy.makeup.consequence("Jonas", "fr. 18. des.")).toBe(
      "Jonas får et eget Klassespill mot tre KI-spillere, åpent til Testfristen fr. 18. des. Jonas får beskjed på Hjem og på e-post.",
    );
    expect(copy.makeup.consequence("Jonas", "fr. 15. mai")).toContain("Testfristen fr. 15. mai. Jonas får");
    expect(copy.makeup.given("12. mai", "fr. 15. mai")).toBe("Oppfølgingsspill gitt 12. mai. Åpent til fr. 15. mai.");
  });
});

describe("a day in May ends its sentence like any other", () => {
  const MAY = "2027-05-12T09:00:00Z";
  it("keeps one full stop after «mai» in every line built from a day", () => {
    expect(completionRows(completion({ steps: completion().steps.map((s) => ({ ...s, recorded_at: MAY })) }))[0]!.lines[0]).toBe(
      "Registrert on. 12. mai.",
    );
    expect(copy.corrected(true, "Bård", "12. mai")).toBe("Gjort, rettet av Bård 12. mai.");
    expect(copy.corrected(true, "Bård", "12. des.")).toBe("Gjort, rettet av Bård 12. des.");
    expect(gameLines({ game_id: "g", number: 3, role: "wholesaler", state: "finished", played_out: false, finished_at: MAY, makeup: false }, (r) => r)[1]).toBe(
      "Ferdig on. 12. mai.",
    );
    expect(debriefLines({ explanation: null, explanation_saved_at: null, finished_at: MAY, late: false, moments: 3 })[0]).toBe(
      "Fullført on. 12. mai. 3 nøkkeløyeblikk.",
    );
    expect(debriefLines({ explanation: null, explanation_saved_at: null, finished_at: MAY, late: false, moments: 0 })[0]).toBe(
      "Fullført on. 12. mai.",
    );
    expect(replayLine({ game_id: "r", finished_at: MAY })).toBe("Ferdig on. 12. mai.");
    expect(nb.reports.record.debrief.sent("on. 12. mai")).toBe("Sendt on. 12. mai.");
  });
});

describe("participation, information only (FR-17)", () => {
  it("gives the time on own Orders and whether they were constant", () => {
    expect(duration(3840)).toBe("1 t 4 min");
    expect(duration(59)).toBe("under 1 min");
    expect(participationLines({ own_orders: 5, seconds: 600, constant: true, after_guided: 4 })).toEqual([
      "Tid på egne bestillinger: 10 min.",
      "De 4 egne bestillingene etter de veiledede ukene hadde samme antall.",
    ]);
    expect(participationLines({ own_orders: 5, seconds: 600, constant: false, after_guided: 4 })[1]).toBe(copy.varied(4));
    expect(participationLines({ own_orders: 1, seconds: 60, constant: null, after_guided: 1 })[1]).toBe(copy.tooFew);
    expect(participationLines(null)).toEqual([copy.noOrders]);
  });
});

describe("the Individual test part", () => {
  it("shows the status and each part, never an answer", () => {
    const found = testLines({
      status: "auto_submitted",
      submitted_at: AT,
      parts: { choice: true, long: false },
    });
    expect(found.lines[0]).toBe(nb.reports.record.test.status.auto_submitted);
    expect(found.parts).toEqual([
      { name: "Flervalg", text: "har svar" },
      { name: "Langsvar", text: "mangler svar" },
    ]);
    expect(testLines(null)).toEqual({ lines: [nb.reports.record.test.none], parts: [] });
  });
});

describe("the record parts (FR-63)", () => {
  const record = nb.reports.record;
  const role = (r: string) => (r === "wholesaler" ? "Grossist" : r);

  it("names the game, its state and its end", () => {
    expect(gameLines(null, role)).toEqual([record.game.none]);
    const game = { game_id: "g", number: 3, role: "wholesaler", state: "running" as const, played_out: false, finished_at: null, makeup: false };
    expect(gameLines(game, role)).toEqual(["Spill 3 · Grossist", record.game.state.running]);
    expect(gameLines({ ...game, state: "finished", played_out: true, finished_at: AT }, role)).toEqual([
      "Spill 3 · Grossist",
      "Ferdig lø. 12. des.",
      record.game.playedOut,
    ]);
    expect(gameLines({ ...game, state: "ended", finished_at: AT }, role)[1]).toBe(record.game.state.ended);
    // Story 13.5: a finished Oppfølgingsspill that became the Student's game.
    expect(gameLines({ ...game, number: null, makeup: true, state: "finished", finished_at: AT }, role)).toEqual([
      "Oppfølgingsspill · Grossist",
      "Ferdig lø. 12. des.",
    ]);
  });

  it("gives the Debrief's state, the quiz attempts and the Replay", () => {
    const none = { explanation: null, explanation_saved_at: null, finished_at: null, late: false, moments: 0 };
    expect(debriefLines(none)).toEqual([record.debrief.notFinished]);
    expect(debriefLines({ ...none, finished_at: AT, moments: 3, late: true })).toEqual([
      "Fullført lø. 12. des. 3 nøkkeløyeblikk.",
      record.debrief.late,
    ]);
    expect(quizLines([])).toEqual([record.quiz.none]);
    const [passed] = quizLines([{ number: 2, submitted_at: AT, passed: true }]);
    expect(passed!.startsWith("Forsøk 2 · lø. 12. des.")).toBe(true);
    expect(passed!.endsWith(" · bestått")).toBe(true);
    expect(quizLines([{ number: 1, submitted_at: AT, passed: false }])[0]!.endsWith(" · ikke bestått")).toBe(true);
    expect(replayLine(null)).toBe(record.replay.none);
    expect(replayLine({ game_id: "r", finished_at: null })).toBe(record.replay.running);
    expect(replayLine({ game_id: "r", finished_at: AT })).toBe("Ferdig lø. 12. des.");
  });
});
