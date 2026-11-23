/**
 * The Student report's PDF copy (Story 13.7, FR-58, FR-72, AD-19): it lives in the print route, in
 * Norwegian bokmål, and `check:copy` reads it. The step names, «gjort» / «ikke gjort», the share
 * lines and the requirement lines are the Studentside's («Fullføring», EXPERIENCE.md); the rest is
 * [ASSUMPTION] draft copy for the founder's review. Stories 13.8 and 13.10 add their sections' copy
 * here.
 */
export const reportCopy = {
  product: "ØL-spillet",
  title: "Studentrapport",
  /** What the report is, under the title (FR-58): it documents work, it is no grade. */
  purpose: "Rapporten dokumenterer arbeidet ditt i Klasseøkten. Den er ikke en karakter.",
  facts: {
    student: "Student",
    klass: "Klasse",
    session: "Klasseøkt",
    generated: "Laget",
  },
  dates: {
    title: "Datoer",
    caption: "Datoene i Klasseøkten",
    name: "Dato",
    when: "Tidspunkt",
    start_at: "Startdato",
    play_deadline: "Spillfrist",
    debrief_deadline: "Debrieffrist",
    test_deadline: "Testfrist",
    none: "Ikke satt",
  },
  completion: {
    title: "Fullføring",
    caption: "Status per steg",
    step: "Steg",
    status: "Status",
    steps: {
      class_game: "Klassespill",
      debrief: "Debrief",
      quiz_passed: "Debrief-quiz",
      replay: "Replay",
      test_submitted: "Individuell test",
    },
    done: "gjort",
    notDone: "ikke gjort",
    /** A Lecturer's correction decided the step; the reason is never in the report. */
    corrected: (status: string) => `${status}, rettet av faglærer`,
    /** «Bestilte selv i 70 % av ukene.» */
    ordered: (percent: string) => `Bestilte selv i ${percent} av ukene.`,
    orderedIn: (percent: string, game: "class" | "makeup") =>
      `Bestilte selv i ${percent} av ukene i ${game === "makeup" ? "Oppfølgingsspillet" : "Klassespillet"}.`,
    required: (percent: string) => `Kravet er ${percent}.`,
    playout: (percent: string) => `${percent} av ukene ble spilt i utspillingen ved Spillfristen.`,
    met: "Kravet er oppfylt.",
    notMet: "Kravet er ikke oppfylt.",
    notObligatory: "Klasseøkten er ikke obligatorisk.",
  },
  /** The game section (Story 13.8, FR-58, FR-34). The chart words and the marks' words are the
   * charts' own (`nb.insight`, `nb.games.play`), as on Spillinnsikt and the play screen. */
  game: {
    classGame: "Klassespill",
    makeup: "Oppfølgingsspill",
    facts: {
      game: "Spill",
      role: "Rolle",
      weeks: "Uker spilt",
      cost: "Totalkostnad",
    },
    /** «36 av 36». */
    weeks: (played: string, total: string | null) => (total === null ? played : `${played} av ${total}`),
    cost: (amount: string) => `${amount} kr`,
    /** A game that ended without its last Uke (closed at the Testfrist) or still open. */
    notFinished: "Spillet ble ikke spilt ferdig. Rapporten viser ukene som ble spilt.",
    none: "Du spilte ikke noe spill i denne Klasseøkten.",
    seat: {
      title: "Din rolle uke for uke",
      intro: (role: string) => `Netto lager, posisjon og kost per uke for deg som ${role}, med tabellen under grafen.`,
      region: (from: number, to: number) => `Din rolle, Uke ${from}–${to}`,
    },
    chain: {
      title: "Hele kjeden",
      intro:
        "Ordre, lager og restordre for alle fire rollene og kundenes etterspørsel, uke for uke. De andre i spillet står bare med rollen sin.",
      block: (from: number, to: number) => `Uke ${from}–${to}`,
    },
    holders: {
      title: "Hvem spilte",
      caption: "Hvem som spilte hver rolle, og merknadene for ukene",
      role: "Rolle",
      playedBy: "Spilt av",
      marks: "Merknader",
      student: "Student",
      ai: "KI-spiller",
      free: "Ledig",
      /** «KI-spiller, Uke 5–20». */
      range: (who: string, from: number, to: number) => (from === to ? `${who}, Uke ${from}` : `${who}, Uke ${from}–${to}`),
      /** «Uke 21: KI tok over etter ventetiden.» */
      mark: (week: number, text: string) => `Uke ${week}: ${text}.`,
      none: "Ingen",
    },
  },
} as const;

const DATE_TIME = new Intl.DateTimeFormat("nb-NO", {
  timeZone: "Europe/Oslo",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** «24. november 2026 kl. 10:00»: an instant in Europe/Oslo, with its year, since a report is
 * read long after. */
export function reportDateTime(iso: string): string {
  return DATE_TIME.format(new Date(iso));
}
