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
    /** «Glemt passord» (Story 3.6, UX-DR61). `sent` is EXPERIENCE.md's own and never says
     * whether the address has an account. */
    forgot: {
      pageTitle: "Glemt passord",
      title: "Glemt passord",
      // [ASSUMPTION] Story 3.6.
      lead: "Skriv e-postadressen til kontoen din. Du får en lenke der du velger et nytt passord.",
      email: "E-post",
      // [ASSUMPTION] Story 3.6.
      submit: "Send lenke",
      sent: "Hvis adressen har en konto, har vi sendt en lenke. Lenken virker i én time.",
      // [ASSUMPTION] Story 3.6: the reset limits count per hour.
      rateLimited: "For mange forespørsler. Prøv igjen om en time.",
      // [ASSUMPTION] Story 3.6.
      failed: "Lenken ble ikke sendt. Prøv igjen.",
    },
    /** «Nytt passord» (Story 3.6, UX-DR61). `invalid`, `sendNew` and `done` are EXPERIENCE.md's
     * own. */
    reset: {
      pageTitle: "Nytt passord",
      title: "Nytt passord",
      // [ASSUMPTION] Story 3.6: the account the link belongs to.
      lead: (email: string) => `Velg et nytt passord for ${email}.`,
      password: "Nytt passord",
      // [ASSUMPTION] Story 3.6: the shortest password is 8 characters.
      passwordRule: "Minst 8 tegn.",
      errors: {
        passwordEmpty: "Skriv et nytt passord.",
        passwordShort: "Passordet må ha minst 8 tegn.",
      },
      // [ASSUMPTION] Story 3.6.
      submit: "Lagre passord",
      invalid: "Lenken er utløpt eller brukt.",
      sendNew: "Send ny lenke",
      done: "Passordet er endret.",
      // [ASSUMPTION] Story 3.6.
      failed: "Passordet ble ikke lagret. Prøv igjen.",
    },
    /** «Du er invitert» (Story 3.8, UX-DR61). `title`, `submit` and the validity sentence are
     * EXPERIENCE.md's own; the epic leaves the expired-link copy to this story. */
    invitation: {
      pageTitle: "Du er invitert",
      title: "Du er invitert",
      // [ASSUMPTION] Story 3.8: the lead names the role the account gets.
      lead: (role: string) => `Du er invitert som ${role} i ØL-spillet. Kontoen får rollen så snart den er laget.`,
      roles: { lecturer: "Faglærer", admin: "Admin" },
      name: "Navn",
      // [ASSUMPTION] Story 3.8: the address comes from the Invitation and cannot be changed.
      email: "E-post, fra Invitasjonen",
      password: "Velg passord",
      // [ASSUMPTION] Story 3.8: the same rule as «Nytt passord».
      passwordRule: "Minst 8 tegn.",
      submit: "Opprett konto og gå videre",
      validity: (days: number) => `Invitasjonen er gyldig i ${days === 1 ? "én dag" : `${days} dager`}.`,
      errors: {
        // [ASSUMPTION] Story 3.8.
        nameEmpty: "Skriv navnet ditt.",
        nameLong: "Navnet kan ha høyst 200 tegn.",
        passwordEmpty: "Skriv et passord.",
        passwordShort: "Passordet må ha minst 8 tegn.",
      },
      // [ASSUMPTION] Story 3.8.
      failed: "Kontoen ble ikke opprettet. Prøv igjen.",
      rateLimited: "For mange forsøk. Prøv igjen om en time.",
      /** The address already has an account: logging in adds the role. [ASSUMPTION] Story 3.8. */
      existing: {
        lead: (role: string) => `Adressen har allerede en konto. Logg inn, så får kontoen rollen ${role}.`,
        email: "E-post",
        password: "Passord",
        submit: "Logg inn og legg til rollen",
        failed: "Rollen ble ikke lagt til. Prøv igjen.",
      },
      /** An expired or used link. `invalid` is the wording of «Nytt passord»; the rest is
       * [ASSUMPTION] Story 3.8. `requested` is the same for every link, so it never says whether
       * the link or an account exists. */
      invalid: "Lenken er utløpt eller brukt.",
      requestNew: "Be om ny Invitasjon",
      requested: "Hvis lenken kom fra en Invitasjon, ser Admin nå at du ber om en ny. Den kommer på e-post.",
      requestFailed: "Forespørselen ble ikke sendt. Prøv igjen.",
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

  /** The Admin-område and its pages (FR-1–FR-3). «Brukere og roller» is EXPERIENCE.md's own. */
  admin: {
    /** The pages the Admin-område links to; later stories add theirs. */
    sections: {
      users: "Brukere og roller",
    },
    users: {
      title: "Brukere og roller",
      invite: {
        // [ASSUMPTION] Story 3.7: the section heading and its lead, which states the consequence.
        title: "Inviter",
        lead: "Invitasjonen gir rollen så snart kontoen er laget. Ingen godkjenning etterpå.",
        email: "E-post",
        role: "Rolle",
        roles: { lecturer: "Faglærer", admin: "Admin" },
        // [ASSUMPTION] Story 3.7: the button says what happens.
        submit: "Send Invitasjon",
        // [ASSUMPTION] Story 3.7: the result line, with the address, the role and the real days.
        sent: (email: string, role: string, days: number) =>
          `Invitasjonen er sendt til ${email} som ${role}. Den er gyldig i ${days === 1 ? "én dag" : `${days} dager`}.`,
        errors: {
          // [ASSUMPTION] Story 3.7: the empty field; the other reasons are those of «Logg inn».
          emailEmpty: "Skriv e-postadressen.",
        },
        // [ASSUMPTION] Story 3.7.
        failed: "Invitasjonen ble ikke sendt. Prøv igjen.",
      },
    },
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

  /** Loading, offline, page and action errors (Story 3.4). All are EXPERIENCE.md's own
   * (State Patterns → All); `sessionExpired` is under `auth.login`. */
  system: {
    loading: "Laster …",
    offline: "Frakoblet. Det du har skrevet, er tatt vare på på denne enheten.",
    reconnected: "Tilkoblet igjen.",
    pageError: "Siden kunne ikke lastes.",
    retry: "Prøv igjen",
    /** «Sist oppdatert 21:14»: the time live values were last read. */
    lastUpdated: (clock: string) => `Sist oppdatert ${clock}`,
    actionFailed: "Det ble ikke lagret. Prøv igjen.",
  },
} as const;
