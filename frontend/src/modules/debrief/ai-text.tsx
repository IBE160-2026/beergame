import { nb } from "@/copy/nb";

import { type RenderedText, shownText } from "./api";

/**
 * Debrief text as shown (Story 9.14, FR-34, FR-44, UX-DR69): code-rendered text as written; AI text
 * as «KI-generert, kan ta feil: «…»» with `data-ai-generated="true"`, the machine-readable marker the
 * print route reuses. Only `ai_generated` decides; the web app never guesses.
 */
export function DebriefText({ text }: { text: RenderedText }) {
  if (!text.ai_generated) return <>{text.text}</>;
  return <span data-ai-generated="true">{shownText(text)}</span>;
}

/** Under an AI text: the AI's explanation can be wrong, and the numbers are the code's (FR-44). */
export function AiNote({ text, className = "" }: { text: RenderedText; className?: string }) {
  if (!text.ai_generated) return null;
  return <p className={`text-caption text-ink-secondary ${className}`}>{nb.debrief.aiNote}</p>;
}
