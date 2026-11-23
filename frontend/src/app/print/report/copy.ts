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
  /** The Debrief section (Story 13.10, FR-58, FR-47). The moments' «Dette regnet du» and «Dette
   * kostet det senere» are the Debrief's and the walkthrough's own words (`nb`). */
  debrief: {
    title: "Debrief",
    explanation: "Forklaringen din",
    /** «Sendt 20. november 2026 kl. 18:00.» */
    sent: (when: string) => `Sendt ${when}.`,
    noExplanation: "Du sendte ingen Forklaring.",
    finished: (when: string) => `Debriefen ble fullført ${when}.`,
    late: (when: string) => `Debriefen ble fullført ${when}, etter Debrieffristen.`,
    notFinished: "Debriefen ble ikke fullført.",
    moments: "Nøkkeløyeblikk",
    /** A finished Debrief whose game had too few of the Student's own Orders for moments. */
    noMoments: "Spillet ditt hadde for få egne ordrer til at Debriefen valgte øyeblikk.",
    week: (week: number) => `Uke ${week}`,
    narration: "Slik henger øyeblikkene sammen",
    reflection: "Spørsmål til ettertanke",
    /** Always under the answers (FR-58): what is left out, and who reads it. */
    reflectionNote:
      "Svarene på spørsmålene om følelser er ikke med i rapporten. Faglærerne og assistentene i Klassen kan lese dem.",
    noReflection: "Ingen svar på spørsmål om bevis og struktur.",
    quiz: "Debrief-quiz",
    /** The number of attempts (FR-47) and whether it is passed. */
    attempts: (attempts: number, passed: boolean) => {
      if (attempts === 0) return "Quizen ble ikke tatt.";
      if (passed) return attempts === 1 ? "Bestått på første forsøk." : `Bestått etter ${attempts} forsøk.`;
      return attempts === 1 ? "1 forsøk, ikke bestått." : `${attempts} forsøk, ikke bestått.`;
    },
  },
  /** The Replay section (Story 13.10, FR-58, FR-50, UX-DR70). The chart's and the table's words are
   * the walkthrough's (`nb.replay.walkthrough`), «Ikke like for like.» among them. */
  replay: {
    title: "Replay",
    none: "Du spilte ikke Replay i denne Klasseøkten.",
    closed: "Replay ble stengt ved Testfristen før siste uke, og ble ikke fullført.",
    open: "Replay er ikke ferdig spilt.",
    scenario: "Replay-scenario",
    scenarioCaption: "Innstillingene i din Replay",
    setting: "Innstilling",
    value: "Verdi",
    facts: {
      role: "Rolle",
      weeks: "Uker",
      guided: "Veiledede uker",
      start: "Start",
      delays: "Forsinkelser",
      costs: "Kostnader",
    },
    /** «12 på lager, 0 i restordre». */
    start: (inventory: string, backlog: string) => `${inventory} på lager, ${backlog} i restordre`,
    /** «Ordre 2 uker, frakt 2 uker, produksjon 2 uker». */
    delays: (order: string, shipping: string, production: string) =>
      `Ordre ${order} uker, frakt ${shipping} uker, produksjon ${production} uker`,
    /** «0,50 kr per enhet på lager, 1,00 kr per enhet i restordre, hver uke». */
    costs: (holding: string, backorder: string) =>
      `${holding} kr per enhet på lager, ${backorder} kr per enhet i restordre, hver uke`,
    weeks: (played: string, total: string) => `${played} av ${total}`,
    cost: (amount: string) => `${amount} kr`,
  },
  /** The Individual test section (Story 13.10, FR-58, C-2). The items' headings and types are the
   * test page's (`nb.tests.individual`). */
  test: {
    title: "Individuell test",
    none: "Du åpnet ikke Individuell test.",
    open: "Testen er ikke levert. Rapporten viser svarene som var lagret.",
    submitted: (when: string) => `Levert ${when}.`,
    autoSubmitted: (when: string) => `Levert automatisk ${when}, med svarene som var lagret.`,
    /** What the points are, once, before the items (C-2: no grade, no AI score). */
    scoring:
      "Poengene for flervalg og interaktive oppgaver er regnet ut av koden. Langsvar og oppgaver fra spillet ditt får ingen poeng her. Testen gir ingen karakter.",
    /** «Poeng regnet ut av koden: 17,5 av 25.» */
    total: (points: string, of: string) => `Poeng regnet ut av koden: ${points} av ${of}.`,
    answer: "Ditt svar",
    /** «Poeng: 7,5 av 15». */
    points: (points: string, of: string) => `Poeng: ${points} av ${of}`,
    notScored: "Ingen poeng her: rettes ikke av koden.",
    /** Under an Interaktiv oppgave's table with an Uke left empty. */
    empty: "– betyr at uka ikke er besvart.",
    region: (caption: string) => `Svaret ditt: ${caption}`,
    /** A number item's column: its headers. */
    column: { row: "Rad", value: "Tall" },
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
