/**
 * All UI copy, in Norwegian bokmål (FR-72, AD-19). Components never hold their own strings.
 *
 * Voice (EXPERIENCE.md → Voice and Tone):
 * - Second person, direct and concrete, in short declarative sentences.
 * - Buttons say what happens, and repeat the number where there is one.
 * - Show the sum, not a verdict. No blame or praise, no hedged or marketing copy, no learning claims.
 * - Faglærer copy states the consequence.
 * - Use Norwegian number format: «2 266,00 kr».
 * - Units are «enheter».
 *
 * `npm run check:copy` (scripts/check-copy.mjs) enforces the hard rules on every string here, in
 * the mail templates and in the print route. It fails on an exclamation mark, on the Norwegian
 * word for beer outside the product name, and on the words for "optimal" and "answer key". It
 * also fails on the English game name and the amplification-effect term in copy shown before
 * the Debrief. Top-level sections shown only from the Debrief on are listed in
 * POST_DEBRIEF_SECTIONS in that script.
 *
 * Strings marked [ASSUMPTION] are drafts until the founder's copy review (Issue #31).
 */
export const nb = {
  product: {
    name: "ØL-spillet",
  },

  /** PRD glossary term → UI string (EXPERIENCE.md → Foundation → Terms). */
  terms: {
    admin: "Admin",
    adminArea: "Admin-område",
    lecturer: "Faglærer",
    assistantLecturer: "Assistent",
    student: "Student",
    user: "bruker",
    institution: "Institusjon",
    invitation: "Invitasjon",
    class: "Klasse",
    roster: "klasseliste",
    classSession: "Klasseøkt",
    gameSettings: "Spillinnstillinger",
    informationVisibility: "Synlige naboer",
    demandPattern: "Etterspørsel",
    game: "Spill",
    classGame: "Klassespill",
    replay: "Replay",
    role: "Rolle",
    retailer: "Detaljist",
    wholesaler: "Grossist",
    distributor: "Distributør",
    factory: "Fabrikk",
    seat: "Sete",
    seats: "Setene",
    week: "Uke",
    order: "Ordre",
    units: "enheter",
    inventory: "Lager",
    backlog: "Restordre",
    incomingOrder: "Ordre inn",
    incomingDelivery: "Levering",
    unitsShipped: "Sendt",
    supplyLine: "På vei",
    netInventory: "Netto lager",
    position: "Posisjon",
    guidedWeeks: "Veiledede uker",
    guidedWeek: "Veiledet uke",
    startingTask: "Startoppgave",
    totalCost: "Totalkostnad",
    chainTotalCost: "Kjedens totalkostnad",
    chainCost: "Kjedekost",
    costPerWeek: "Kost per uke",
    orderAmplification: "Forsterkning",
    detectedPatterns: "Mønstre",
    aiPlayer: "KI-spiller",
    llmPlayer: "LLM-spiller",
    ruleBasedPlayer: "regelbasert KI-spiller",
    aiMode: "KI-modus",
    effortLevel: "Innsatsnivå",
    inactivityLimit: "Ventetid før KI tar over",
    pause: "Pause",
    reclaim: "Ta tilbake setet",
    labHour: "Labtime",
    startDate: "Startdato",
    playDeadline: "Spillfrist",
    debriefDeadline: "Debrieffrist",
    testDeadline: "Testfrist",
    explanation: "Forklaring",
    groupDebrief: "Gruppedebrief",
    personalDebrief: "Personlig debrief",
    debriefQuiz: "Debrief-quiz",
    individualTest: "Individuell test",
    interactiveItem: "Interaktiv oppgave",
    coreItems: "Faste oppgaver",
    adaptedItems: "Tilpassede oppgaver",
    itemWeight: "Vekt",
    scoringGuide: "Sensorveiledning",
    controlTest: "Kontrolltest",
    aiAssessment: "KI-vurdering",
    indicativeLetter: "Veiledende bokstav",
    studentReport: "Studentrapport",
    completionStatus: "Fullføring",
    completionExport: "fullføringsliste",
    makeupGame: "Oppfølgingsspill",
    adjustment: "Tilrettelegging",
    inTheRoom: "I rommet",
    obligatory: "Obligatorisk",
    lecturerOverview: "Oversikt",
    gameInsight: "Spillinnsikt",
    classReport: "Klasserapport",
    crossClassStatistics: "Tverrklasse-statistikk",
    message: "Melding",
    demoData: "Demodata",
    simulated: "Simulert",
  },

  auth: {
    login: {
      pageTitle: "Logg inn",
      title: "Logg inn",
      // [ASSUMPTION] EXPERIENCE.md says only "E-post og passord. Ingen åpen registrering".
      lead: "Kontoer lages bare fra en Invitasjon på e-post.",
      email: "E-post",
      password: "Passord",
      submit: "Logg inn",
      forgotPassword: "Glemt passord?",
      errors: {
        // [ASSUMPTION] for the empty and «Mangler navnet før @» and space reasons;
        // «Mangler @», «To @» and «Domene mangler» are EXPERIENCE.md's own.
        emailEmpty: "Skriv e-postadressen din.",
        emailNoAt: "Mangler @",
        emailTwoAt: "To @",
        emailNoLocal: "Mangler navnet før @",
        emailNoDomain: "Domene mangler",
        emailSpace: "Fjern mellomrommet",
        passwordEmpty: "Skriv passordet ditt.",
      },
      // EXPERIENCE.md → State Patterns → Account and access. `deactivated` shows only after the
      // right password; its staff wording is open in Issue #31.
      invalidCredentials: "Feil e-post eller passord.",
      deactivated: "Kontoen er deaktivert. Ta kontakt med faglæreren din.",
      sessionExpired: "Du er logget ut. Logg inn igjen for å fortsette.",
      // [ASSUMPTION] Story 3.2: too many failed logins, and any other failure.
      rateLimited: "For mange forsøk. Vent noen minutter og prøv igjen.",
      failed: "Innloggingen gikk ikke. Prøv igjen.",
    },
    session: {
      // [ASSUMPTION] Story 3.2.
      logout: "Logg ut",
      logoutFailed: "Utloggingen gikk ikke. Prøv igjen.",
    },
  },

  /** The three homes (Story 3.3, UX-DR77). Their h1 is the page name. */
  homes: {
    adminArea: "Admin-område",
    lecturerHome: "Lærerhjem",
    home: "Hjem",
  },

  /** Links between pages (Story 3.3). Each names where it goes. */
  navigation: {
    // «Til Hjem» and «Til Lærerhjem» are EXPERIENCE.md's own (State Patterns → permission denied).
    toHome: "Til Hjem",
    toLecturerHome: "Til Lærerhjem",
    // [ASSUMPTION] the Admin's home, and the Lærerhjem → Admin-område link (FR-2).
    toAdminArea: "Til Admin-område",
    // [ASSUMPTION] the not-found page's link for a visitor who is not logged in.
    toLogin: "Til innlogging",
    // [ASSUMPTION] the accessible name of the staff breadcrumb.
    breadcrumb: "Du er her",
  },

  /** EXPERIENCE.md → State Patterns (UX-DR59). */
  access: {
    denied: "Du har ikke tilgang til denne siden.",
    notFound: "Fant ikke siden.",
  },
} as const;
