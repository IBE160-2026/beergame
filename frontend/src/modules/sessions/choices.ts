import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import type { AiMode, ClassSession } from "./api";

const copy = nb.sessions.choices;

export type DebriefMode = ClassSession["debrief_mode"];
/** When the Debriefs open (Story 9.2): each once its game has finished, or all once every Class
 * game has. */
export type DebriefRelease = ClassSession["debrief_release"];
export type OfferedLevel = ClassSession["effort_levels"][number];

/** KI-modus, Innsatsnivå and Debrief-modus (Story 5.5), and Obligatorisk with its required share
 * (Story 5.7), as chosen on the screen. They take effect only when «Lagre Klasseøkt» sends them. */
export type ChoicesDraft = {
  aiMode: AiMode;
  /** The chosen level's name; null when nothing is offered. */
  effortLevel: string | null;
  debriefMode: DebriefMode;
  debriefRelease: DebriefRelease;
  /** «KI-tekst i Debriefen» (Story 9.14): on, or a code-only Debrief. */
  debriefAiText: boolean;
  obligatory: boolean;
  /** «Andel uker som kreves» as typed. */
  requiredShare: string;
};

/** The level the screen preselects: the one in force, else the config's default. */
function defaultLevel(levels: readonly OfferedLevel[]): string | null {
  return (levels.find((level) => level.default) ?? levels[0])?.name ?? null;
}

/** The choices as the api returned them. A level in force that is no longer offered gives way to
 * the default, so the screen never sends back a level it cannot show as chosen. */
export function choicesOf(item: ClassSession): ChoicesDraft {
  const offered = item.effort_levels.some((level) => level.name === item.effort_level);
  return {
    aiMode: item.ai_mode,
    effortLevel: offered ? item.effort_level : (defaultLevel(item.effort_levels) ?? item.effort_level),
    debriefMode: item.debrief_mode,
    debriefRelease: item.debrief_release,
    debriefAiText: item.debrief_ai_text,
    obligatory: item.obligatory,
    requiredShare: String(item.required_share_percent),
  };
}

/** A new AI mode: back to LLM players preselects the level in force, else the default. */
export function withAiMode(draft: ChoicesDraft, aiMode: AiMode, item: ClassSession): ChoicesDraft {
  const levels = item.effort_levels;
  const kept = levels.some((level) => level.name === draft.effortLevel) ? draft.effortLevel : null;
  return { ...draft, aiMode, effortLevel: kept ?? choicesOf(item).effortLevel };
}

/** The choices as «Lagre Klasseøkt» sends them: an Effort level only with LLM players, and the
 * required share only while Obligatorisk is on (off, the stored share is kept). Check the share
 * with `shareProblem` first. */
export function choicesBody(draft: ChoicesDraft): {
  ai_mode: AiMode;
  effort_level?: string;
  debrief_mode: DebriefMode;
  debrief_release: DebriefRelease;
  debrief_ai_text: boolean;
  obligatory: boolean;
  required_share_percent?: number;
} {
  return {
    ai_mode: draft.aiMode,
    ...(draft.aiMode === "llm" && draft.effortLevel ? { effort_level: draft.effortLevel } : {}),
    debrief_mode: draft.debriefMode,
    debrief_release: draft.debriefRelease,
    debrief_ai_text: draft.debriefAiText,
    obligatory: draft.obligatory,
    ...(draft.obligatory ? { required_share_percent: Number(draft.requiredShare.trim()) } : {}),
  };
}

/** The level's name as the config gives it. */
export function levelLabel(level: Pick<OfferedLevel, "name" | "label">): string {
  return level.label ?? level.name;
}

/** The one line on a level's effect on speed and cost: the measured figures when the level has
 * them, else the config's line (a placeholder until the prototype), else that it is not measured. */
export function effectLine(level: OfferedLevel): string {
  const seconds = level.time_per_order_median_s ? formatNumber(level.time_per_order_median_s) : null;
  const cost = level.cost_per_game_usd ? formatNumber(level.cost_per_game_usd) : null;
  if (seconds && cost) return copy.effectMeasured(seconds, cost);
  if (seconds) return copy.effectSeconds(seconds);
  if (cost) return copy.effectCost(cost);
  return level.effect ?? copy.effectUnknown;
}

export type DescriptionBlock = { kind: "paragraph"; text: string } | { kind: "list"; items: string[] };

/** An AI player description from the api (Markdown: a title line, paragraphs and `- ` lists) as
 * blocks to render. The title is dropped: the disclosure names the type. */
export function descriptionBlocks(text: string): DescriptionBlock[] {
  const blocks: DescriptionBlock[] = [];
  // Only the title line goes.
  const body = text.replace(/^\s*#\s[^\n]*\n?/, "");
  for (const chunk of body.split(/\n\s*\n/)) {
    const lines = chunk
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line);
    let paragraph: string[] = [];
    let list: string[] = [];
    const flush = () => {
      if (paragraph.length) blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
      if (list.length) blocks.push({ kind: "list", items: list });
      paragraph = [];
      list = [];
    };
    for (const line of lines) {
      if (line.startsWith("- ")) {
        if (paragraph.length) {
          blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
          paragraph = [];
        }
        list.push(line.slice(2));
      } else {
        if (list.length) {
          blocks.push({ kind: "list", items: list });
          list = [];
        }
        paragraph.push(line);
      }
    }
    flush();
  }
  return blocks;
}

/** The allocation method as «Lagre Klasseøkt» sends it (Story 5.17): only a change to Student
 * choice, which opens the Students' choice; nothing otherwise, so the stored method stays and a
 * screen without `FEATURE_STUDENT_CHOICE` never sends one. */
export function methodBody(
  method: ClassSession["allocation_method"],
  item: Pick<ClassSession, "allocation_method">,
): { allocation_method?: "student_choice" } {
  return method === "student_choice" && item.allocation_method !== "student_choice"
    ? { allocation_method: "student_choice" }
    : {};
}
