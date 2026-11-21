/** Stand-in answers of the reflection questions (Story 9.6): the three placeholders of content
 * version 1, feelings, then evidence, then structure. */
export const QUESTIONS = [
  {
    id: "feelings",
    kind: "feelings",
    prompt: "Hvordan opplevde du det å bestille uke for uke uten å vite hva kundene ville bestille?",
    hint: null,
  },
  {
    id: "evidence",
    kind: "evidence",
    prompt: "Hva i tallene fra hele kjeden viser at svingningene vokste oppover i kjeden?",
    hint: null,
  },
  {
    id: "structure",
    kind: "structure",
    prompt: "Hvorfor svinger nesten alle kjeder slik, uansett hvem som spiller dem?",
    hint: "Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.",
  },
] as const;

/** No questions: the section shows nothing (for the specs of the other steps). */
export const NO_REFLECTION = { version: 1, questions: [] };
