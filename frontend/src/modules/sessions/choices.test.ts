import { describe, expect, it } from "vitest";

import { nb } from "@/copy/nb";

import type { ClassSession } from "./api";
import { choicesBody, choicesOf, descriptionBlocks, effectLine, levelLabel, type OfferedLevel, withAiMode } from "./choices";

const c = nb.sessions.choices;

function level(changes: Partial<OfferedLevel> = {}): OfferedLevel {
  return {
    name: "standard",
    label: "Standard",
    effect: null,
    default: true,
    time_per_order_median_s: null,
    cost_per_game_usd: null,
    ...changes,
  };
}

const LEVELS = [level(), level({ name: "careful", label: "Grundig", default: false })];

function session(changes: Partial<ClassSession> = {}): ClassSession {
  return {
    ai_mode: "llm",
    effort_level: "standard",
    effort_levels: LEVELS,
    debrief_mode: "group",
    obligatory: false,
    required_share_percent: 80,
    ...changes,
  } as ClassSession;
}

const MARK = { obligatory: false, requiredShare: "80" };

describe("choices", () => {
  it("start from the api's values, the default level when none is in force", () => {
    expect(choicesOf(session())).toEqual({ aiMode: "llm", effortLevel: "standard", debriefMode: "group", ...MARK });
    expect(choicesOf(session({ obligatory: true, required_share_percent: 60 }))).toMatchObject({
      obligatory: true,
      requiredShare: "60",
    });
    expect(choicesOf(session({ ai_mode: "rule_based", effort_level: null })).effortLevel).toBe("standard");
    expect(choicesOf(session({ effort_levels: [], effort_level: null })).effortLevel).toBeNull();
    // A level in force that is no longer offered gives way to the default.
    expect(choicesOf(session({ effort_level: "gone" })).effortLevel).toBe("standard");
    expect(choicesOf(session({ effort_level: "gone", effort_levels: [] })).effortLevel).toBe("gone");
  });

  it("send a level only with LLM players", () => {
    const draft = { aiMode: "llm" as const, effortLevel: "careful", debriefMode: "personal" as const, ...MARK };
    expect(choicesBody(draft)).toEqual({
      ai_mode: "llm",
      effort_level: "careful",
      debrief_mode: "personal",
      obligatory: false,
    });
    expect(choicesBody({ ...draft, aiMode: "rule_based" })).toEqual({
      ai_mode: "rule_based",
      debrief_mode: "personal",
      obligatory: false,
    });
    expect(choicesBody({ ...draft, effortLevel: null })).toEqual({
      ai_mode: "llm",
      debrief_mode: "personal",
      obligatory: false,
    });
  });

  it("send the required share only while Obligatorisk is on", () => {
    const draft = { aiMode: "rule_based" as const, effortLevel: null, debriefMode: "group" as const };
    expect(choicesBody({ ...draft, obligatory: true, requiredShare: " 75 " })).toEqual({
      ai_mode: "rule_based",
      debrief_mode: "group",
      obligatory: true,
      required_share_percent: 75,
    });
    expect(choicesBody({ ...draft, obligatory: false, requiredShare: "0" })).not.toHaveProperty(
      "required_share_percent",
    );
  });

  it("keep the chosen level across a switch of AI mode", () => {
    const item = session();
    const chosen = { aiMode: "llm" as const, effortLevel: "careful", debriefMode: "group" as const, ...MARK };
    const away = withAiMode(chosen, "rule_based", item);
    expect(withAiMode(away, "llm", item).effortLevel).toBe("careful");
    expect(withAiMode({ ...chosen, effortLevel: null }, "llm", item).effortLevel).toBe("standard");
  });
});

describe("effort levels", () => {
  it("are named by the config's label, else their name", () => {
    expect(levelLabel(level())).toBe("Standard");
    expect(levelLabel(level({ label: null }))).toBe("standard");
  });

  it("say their effect in one line: the measured figures, else the config's, else not measured", () => {
    expect(effectLine(level({ effect: "Raskest og billigst." }))).toBe("Raskest og billigst.");
    expect(effectLine(level({ effect: "Plassholder.", cost_per_game_usd: "0.04" }))).toBe(c.effectCost("0,04"));
    expect(effectLine(level({ time_per_order_median_s: "1.2", cost_per_game_usd: "0.04" }))).toBe(
      c.effectMeasured("1,2", "0,04"),
    );
    expect(effectLine(level({ time_per_order_median_s: "1.2" }))).toBe(c.effectSeconds("1,2"));
    expect(effectLine(level({ cost_per_game_usd: "0.04" }))).toBe(c.effectCost("0,04"));
    expect(effectLine(level())).toBe(c.effectUnknown);
  });
});

describe("descriptionBlocks", () => {
  it("drops the title and keeps paragraphs and lists in order", () => {
    const text = "# Regelbasert KI-spiller\n\nFørste avsnitt\nfortsetter.\n# ikke en tittel\n\nDen ser på:\n- eget lager\n- egen restordre\n\nSiste.";
    expect(descriptionBlocks(text)).toEqual([
      { kind: "paragraph", text: "Første avsnitt fortsetter. # ikke en tittel" },
      { kind: "paragraph", text: "Den ser på:" },
      { kind: "list", items: ["eget lager", "egen restordre"] },
      { kind: "paragraph", text: "Siste." },
    ]);
  });
});
