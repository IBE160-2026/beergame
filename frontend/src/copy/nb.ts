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

const COUNT_WORDS = ["null", "én", "to", "tre", "fire", "fem", "seks", "sju", "åtte", "ni", "ti", "elleve", "tolv"];

/** A small count as a word in running text («unntatt fire»); 13 and up as a number. */
function countWord(count: number): string {
  return COUNT_WORDS[count] ?? String(count);
}

/** «1 enhet», «6 enheter» (a capacity is 1 to 100, so no digit grouping). */
const unitsText = (units: number) => `${units} ${units === 1 ? "enhet" : "enheter"}`;

/** The Start-date line of «Du er invitert» and Hjem (Story 4.5). [ASSUMPTION] EXPERIENCE.md's draft:
 * a Student sees game, Role and Seats from the Start date (founder decision 2026-11-12). */
const START_DATE_LINE = "Du får Rolle og spill på startdatoen.";

/** Story 6.20: the plain-text label of a Lecturer's test Game, where a Class game reads «Spill 17»
 * (UX-DR70); never «Demodata». [ASSUMPTION] draft copy, not in the spine. */
const TEST_GAME = "Testspill";

/** «fire uker», «to uker»: a number of Uker in words, as the projection's sentence says it (Story
 * 10.4); the delays make it 2 to 6, a larger one stays a figure. */
const WEEK_WORDS = ["null uker", "én uke", "to uker", "tre uker", "fire uker", "fem uker", "seks uker"];
const weeksInWords = (weeks: number) => WEEK_WORDS[weeks] ?? `${weeks} uker`;

/** A sum kept on one line: its spaces made non-breaking, so «−4 − 4 × 10 = −44» never breaks
 * inside (the projection's sentence, Story 10.6 fix of the 10.4 visual check). Where a line is
 * narrower than the sum, the sentence's `overflow-wrap` breaks it rather than the page scroll. */
const formula = (sum: string) => sum.replaceAll(" ", " ");

/** «Spill 17», or «Testspill» for a test Game, which has no number (Story 6.20). */
/** A day ending a sentence: «12. des.» keeps its full stop, «15. mai» gets one (Story 13.4). */
const sentence = (text: string) => (text.endsWith(".") ? text : `${text}.`);

const gameName = (number: number | null) => (number === null ? TEST_GAME : `Spill ${number}`);

/** Story 6.5: a game the lock has not given its snapshot yet. [ASSUMPTION] */
const NOT_READY = "Spillet er ikke klart til å starte ennå.";

/** The numbers the briefing's worked Uke writes into its lines (Story 6.2). */
type WorkedWeekCopy = {
  inventoryBefore: number;
  backlogBefore: number;
  onHand: number;
  owed: number;
  shipped: number;
  inventoryAfter: number;
  backlogAfter: number;
};

/** What a Class session on the Lærerhjem still lacks, in words (Stories 5.2, 5.9). */
const LACKS = { dates: "datoer", allocation: "bekreftet fordeling" } as const;

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

  /** The Landing at `/` (Story 3.13, UX-DR61, UX-DR70). The headline, «Be om lærertilgang», the
   * Seat caption, «Demodata» and the line about the class's stock curves are the story's and
   * EXPERIENCE.md's own. The page holds no week counts, prices, customers, quotes or learning
   * claims: `npm run check:copy` checks this section for them. */
  landing: {
    headline: "Hver uke har en strek og et tall. Studentene ser begge.",
    // [ASSUMPTION] Story 3.13: the mockup's lead (01-landing.png) with its subject added.
    lead: "ØL-spillet kjører hele forsyningskjedeøvelsen for emnet ditt, fra Invitasjon til PDF-rapport. På norsk, på mobil, for klasser på rundt 250 studenter.",
    requestAccess: "Be om lærertilgang",
    login: "Logg inn",
    seat: {
      caption: "Ett sete, Grossist, Uke 4. Veiledet uke.",
      // The mockup's note (01-landing.png); Story 6.8 brings back its line about the graph's time
      // axis, now that the figure has one. [ASSUMPTION]
      ownNumbers: "Studenten ser bare sine egne tall. Tidsaksen slutter fire uker etter nå.",
      demoData: "Demodata",
      classCurves: "Lagerkurvene for hele klassen ser du først når du er logget inn.",
    },
    /** The second figure (Story 7.2, UX-DR70): the Matrisevegg with bundled demo data. */
    wall: {
      title: "Alle spillene på én skjerm",
      /** [ASSUMPTION] the line under the title. */
      lead: "Hver rad er ett spill og hver rute én uke, farget etter netto lager.",
    },
  },

  /** «Be om lærertilgang» (Story 3.13, UX-DR61): a short public form the Admin answers by e-mail.
   * EXPERIENCE.md leaves it undrawn; [ASSUMPTION] Story 3.13, all of it. `sent` is the same for
   * every address, so it never says whether one has an account. */
  accessRequest: {
    pageTitle: "Be om lærertilgang",
    title: "Be om lærertilgang",
    lead: "Det finnes ingen åpen registrering. Admin leser forespørselen og sender deg en Invitasjon på e-post.",
    name: "Navn",
    email: "E-post",
    institution: "Institusjon",
    submit: "Send forespørsel",
    sent: "Forespørselen er sendt. Admin svarer deg på e-post.",
    toLanding: "Til forsiden",
    errors: {
      nameEmpty: "Skriv navnet ditt.",
      nameLong: "Navnet kan ha høyst 200 tegn.",
      emailEmpty: "Skriv e-postadressen din.",
      institutionEmpty: "Skriv navnet på Institusjonen.",
      institutionLong: "Navnet kan ha høyst 200 tegn.",
      institutionInvalid: "Navnet kan ikke inneholde @ eller kontrolltegn.",
    },
    rateLimited: "For mange forespørsler. Prøv igjen om en time.",
    failed: "Forespørselen ble ikke sendt. Prøv igjen.",
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
      // [ASSUMPTION] Issue #91: a manually registered Student's account has no password yet.
      firstLead: (email: string) => `Velg et passord for ${email}. Du bruker det til å logge inn.`,
      firstPassword: "Passord",
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
      // The window differs between the limits that apply, so no time is named.
      rateLimited: "For mange forsøk. Vent litt og prøv igjen.",
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
      // Story 4.5: the same line for a role and a Student link, so it names whoever sent it.
      requested: "Hvis lenken kom fra en Invitasjon, ser den som sendte den nå at du ber om en ny. Den kommer på e-post.",
      requestFailed: "Forespørselen ble ikke sendt. Prøv igjen.",
      /** A Student Invitation (Story 4.5): the Class and its Lecturer, after mockup 04's
       * «Faglærer Bård har lagt deg til i class-of-1994, IBE160.». `startDate` is EXPERIENCE.md's
       * draft (founder decision 2026-11-12); the rest is [ASSUMPTION] Story 4.5. */
      student: {
        lead: (inviter: string | null, classLabel: string) =>
          inviter ? `Faglærer ${inviter} har lagt deg til i ${classLabel}.` : `Du er lagt til i ${classLabel}.`,
        // EXPERIENCE.md's terms table and mockup 04 draw this label.
        email: "E-post, fra klasselisten",
        startDate: START_DATE_LINE,
        existing: {
          lead: (classLabel: string) => `Adressen har allerede en konto. Logg inn, så blir du med i ${classLabel}.`,
          submit: "Logg inn og bli med i Klassen",
          failed: "Du ble ikke med i Klassen. Prøv igjen.",
        },
      },
      /** An Assistant lecturer Invitation (Story 4.9, FR-10). [ASSUMPTION] Story 4.9. */
      assistant: {
        lead: (inviter: string | null, classLabel: string) =>
          inviter
            ? `Faglærer ${inviter} har invitert deg som Assistent i ${classLabel}. Du får tilgang bare til denne Klassen.`
            : `Du er invitert som Assistent i ${classLabel}. Du får tilgang bare til denne Klassen.`,
        existing: {
          lead: (classLabel: string) => `Adressen har allerede en konto. Logg inn, så blir du Assistent i ${classLabel}.`,
          submit: "Logg inn og bli Assistent",
        },
      },
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
    /** Hjem names each Class the Student is in, with the Start-date line (Story 4.5). */
    startDate: START_DATE_LINE,
    // [ASSUMPTION] Issue #93: Hjem with no Class (none yet, removed, or archived).
    noClass: "Du er ikke med i noen Klasse nå. Når en Faglærer legger deg til, står Klassen her.",
    /** Hjem from the Start date (Story 6.1, UX-DR29, EXPERIENCE.md → Hjem (Student), mockup
     * `04-student-hjem.png`). «Spill 17 · Du er Grossist», «Setene», «Stegene», «pågår», «Neste
     * frist», the Replay and Individuell test lock lines are the spine's; the rest is
     * [ASSUMPTION] draft copy for review. */
    student: {
      /** «Spill 17 · Du er Grossist». */
      game: (number: number | null, role: string) => `${gameName(number)} · Du er ${role}`,
      /** Shown above a session's block only when the Class has more than one: «Klasseøkt 2». */
      session: (number: number) => `Klasseøkt ${number}`,
      seats: "Setene",
      aiPlayer: "KI-spiller",
      // [ASSUMPTION]
      free: "ledig",
      // [ASSUMPTION] A classmate removed from the Class since the start.
      removed: "Ikke lenger i Klassen",
      /** After the Student's own name on their Seat: «Sara (deg)». [ASSUMPTION] */
      you: (name: string) => `${name} (deg)`,
      /** The own Seat of a Lecturer's test Game, who is no Student of the Class (Story 6.20).
       * [ASSUMPTION] */
      youAlone: "Deg",
      /** Setestatus (Story 6.14, FR-25, UX-DR25, EXPERIENCE.md → Setestatus): the status words and
       * «Venter på: Jonas (3 min) og deg.» are the spine's; `guardSwitched` and the duration units
       * are [ASSUMPTION] draft copy. */
      status: {
        ordered: "har bestilt",
        waiting: "venter",
        waitingFor: (duration: string) => `venter, ${duration}`,
      },
      /** A Seat whose LLM player the Play guard switched (FR-79), also when the switch came before
       * a later Takeover or Reclaim (Story 8.2). [ASSUMPTION] */
      guardSwitched: "KI-spiller (regelbasert)",
      /** Takeover (Story 8.2, FR-36, FR-37, UX-DR62, UX-DR69, EXPERIENCE.md → Takeover): the row
       * «Fabrikk  KI-spiller  bestiller for Jonas» and «KI-spiller har bestilt for deg.» are the
       * spine's; the own row's words, the row of a Student no longer in the Class and the
       * requirement warning are [ASSUMPTION] draft copy. */
      takeover: {
        orderingFor: (name: string) => `bestiller for ${name}`,
        orderingForYou: "bestiller for deg",
        orderingForSeat: "bestiller for setet",
        /** One polite line per Seat taken over: «Fabrikk: KI-spiller bestiller for Jonas.» */
        announced: (role: string, status: string) => `${role}: KI-spiller ${status}.`,
        takenOver: "KI-spiller har bestilt for deg.",
        /** FR-17, FR-14: the only place the product builds this warning (the mail's twin is
         * `_takeover_warning.j2`). Never a number or how many Uker: `check:copy` fails on a digit
         * or «uke» here. */
        requirementWarning:
          "Klassespillet er obligatorisk. At en KI-spiller bestiller for deg, kan påvirke om du oppfyller kravet.",
        /** «Ta tilbake setet» (Story 8.4, FR-37) is the spine's; the line that replaces it, the
         * refusals and the failure are [ASSUMPTION] draft copy. Never how many Uker remain. */
        reclaim: "Ta tilbake setet",
        reclaimQueued: "Du får setet tilbake når neste Uke åpner.",
        reclaimRefusals: {
          seat_not_yours: "Setet er ikke ditt å ta tilbake.",
          game_finished: "Spillet er ferdig.",
          game_not_running: "Spillet er ikke i gang.",
          /** Story 8.14 [ASSUMPTION] the Play deadline playout took the game over. */
          play_deadline_passed: "Spillfristen er nådd, og KI-spillere har tatt over spillet.",
        } as Record<string, string>,
        reclaimFailed: "Setet ble ikke tatt tilbake. Prøv igjen.",
      },
      /** The Student's own Tilrettelegging under Stegene (Story 8.9, FR-17, UX-DR53, EXPERIENCE.md
       * → Tilrettelegging → Student's own view): the spine's lines. Only that Student reads them. */
      adjustment: {
        /** «Du har mer tid før en KI-spiller tar setet ditt (2 × vanlig ventetid).» */
        moreTime: (factor: string) =>
          `Du har mer tid før en KI-spiller tar setet ditt (${factor} vanlig ventetid).`,
        /** «For deg er kravet 60 % av ukene.» */
        share: (percent: string) => `For deg er kravet ${percent} av ukene.`,
      },
      /** «Sett inn KI-spiller» on another Student's Setestatus row (Story 8.8, FR-89, UX-DR27,
       * EXPERIENCE.md → Sett inn KI-spiller and State Patterns → Student game). The two lines before
       * the insert time are the spine's; the button, its consequence and «Sara har allerede satt
       * inn en KI-spiller.» are Spillstyring's (`nb.spillstyring`). The staff line, the refusals and
       * the failure are [ASSUMPTION] draft copy. Never why one Seat's time is later. */
      insert: {
        /** With the Lecturer's agreed time: «Avtalt tid to. 19:00. Etter det kan dere sette inn en
         * KI-spiller.» */
        agreed: (when: string) => `Avtalt tid ${when}. Etter det kan dere sette inn en KI-spiller.`,
        /** The Seat's own insert time: «Etter on. 10:00 kan dere sette inn en KI-spiller.» */
        after: (when: string) => `Etter ${when} kan dere sette inn en KI-spiller.`,
        /** [ASSUMPTION] a Lecturer or Assistant lecturer put the AI player in first. */
        takenByStaff: "Faglæreren har allerede satt inn en KI-spiller.",
        refusals: {
          insert_not_allowed_yet: "Det er ikke tid for å sette inn en KI-spiller ennå.",
          seat_not_yours: "Du kan bare sette inn en KI-spiller fra ditt eget sete i spillet.",
          order_exists: "Studenten har bestilt nå.",
          seat_not_student_held: "Ingen student har dette setet nå.",
          game_not_running: "Spillet er ikke i gang.",
          takeover_not_allowed: "KI-spiller kan ikke settes inn i dette spillet.",
          play_deadline_passed: "Spillfristen er nådd, og KI-spillere har tatt over spillet.",
        } as Record<string, string>,
        failed: "KI-spilleren ble ikke satt inn. Prøv igjen.",
      },
      /** Pausevalg and the pause lines (Story 8.6, FR-89, UX-DR26, UX-DR62, EXPERIENCE.md →
       * Pausevalg and State Patterns → Student game): «Ta pause», the two consequence lines, «Ta
       * pause uten avtalt tid», «Avbryt», «Pause, satt av Sara.» and «Pausen er over. Sara har
       * bestilt.» are the spine's; the reader's own lines («deg», «Du»), the line for a Student no
       * longer in the Class, the refusals and the failure are [ASSUMPTION] draft copy. Never how
       * many Uker remain (FR-14). */
      pause: {
        open: "Ta pause",
        noTakeover: "Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.",
        onlyLecturer:
          "Bare faglæreren kan avtale et tidspunkt. Uten det har hver av dere sin vanlige ventetid før en KI-spiller kan settes inn.",
        confirm: "Ta pause uten avtalt tid",
        cancel: "Avbryt",
        pausedBy: (name: string) => `Pause, satt av ${name}.`,
        pausedByYou: "Pause, satt av deg.",
        pausedByUnknown: "Pause, satt av en annen student.",
        endedBy: (name: string) => `Pausen er over. ${name} har bestilt.`,
        endedByYou: "Pausen er over. Du har bestilt.",
        endedByUnknown: "Pausen er over. En annen student har bestilt.",
        /** Story 8.7 (UX-DR62): the Lecturer paused, or set the agreed time. Only the Lecturer's
         * line carries a time. */
        pausedByLecturer: "Pause, satt av faglæreren.",
        pausedUntil: (when: string) => `Pause til ${when}, satt av faglæreren.`,
        /** [ASSUMPTION] the Lecturer ended the Pause with «Avslutt pausen». */
        endedByLecturer: "Pausen er over. Faglæreren har avsluttet den.",
        refusals: {
          seat_not_yours: "Du har ikke et sete i dette spillet nå.",
          game_finished: "Spillet er ferdig.",
          game_not_running: "Spillet er ikke i gang.",
          pause_not_allowed: "Dette spillet kan ikke settes på pause.",
          play_deadline_passed: "Spillfristen er nådd, og KI-spillere har tatt over spillet.",
        } as Record<string, string>,
        failed: "Spillet ble ikke satt på pause. Prøv igjen.",
      },
      /** «I rommet» above Setestatus (Story 8.11, FR-36, UX-DR62, EXPERIENCE.md → State Patterns →
       * Student game): the line is the spine's, with the reader's own minutes (Tilrettelegging); the
       * line read out when the mark ends is [ASSUMPTION] draft copy. Never another's minutes. */
      inRoom: {
        line: (until: string, minutes: number) =>
          `I rommet til kl. ${until}. En KI-spiller tar setet etter ${minutes}\u00a0min uten ordre.`,
        /** [ASSUMPTION] read out (not shown) when the mark ends while the page is open. */
        ended: "Spillet er ikke i rommet lenger. Den vanlige ventetiden gjelder igjen.",
      },
      /** With non-breaking spaces, so «min» never wraps away from its number (Epic 7 close-out). */
      duration: {
        underMinute: "under 1 min",
        minutes: (n: number) => `${n} min`,
        hours: (n: number) => `${n} t`,
        days: (n: number) => `${n} d`,
      },
      /** One waited-for Seat in «Venter på»: «Jonas (3 min)», «Fabrikk», «deg». */
      waitedFor: (who: string, duration: string | null) => (duration ? `${who} (${duration})` : who),
      waitingYou: "deg",
      waitingOn: (who: string) => `Venter på: ${who}.`,
      steps: "Stegene",
      stepNames: {
        class_game: "Klassespill",
        debrief: "Debrief",
        quiz: "Quiz",
        replay: "Replay",
        test: "Individuell test",
        report: "Rapport",
      },
      /** The current step's mark, in text. */
      current: "pågår",
      // [ASSUMPTION] A step that is done.
      done: "ferdig",
      /** What opens each later step. Replay's and Individuell test's are the spine's; the other
       * four are [ASSUMPTION] in their pattern. */
      locked: {
        class_game: "Klassespill, åpnes på startdatoen.",
        debrief: "Debrief, åpnes når Klassespillet er ferdig.",
        quiz: "Quiz, åpnes når du har fullført Debriefen.",
        replay: "Replay, åpnes når du har bestått Debrief-quizen.",
        test: "Individuell test, åpnes når du har fullført Replay.",
        report: "Rapport, åpnes når den individuelle testen er vurdert.",
      },
      /** Story 9.2: the Debrief step while the Faglærer holds every Debrief until all Class games
       * have finished; never how many remain. [ASSUMPTION] */
      held: {
        debrief: "Debrief, åpnes når alle Klassespillene er ferdige.",
      },
      /** Story 13.5: the Debrief step of a Student with no Class game while their
       * Oppfølgingsspill is not finished. [ASSUMPTION] */
      debriefAfterMakeup: "Debrief, åpnes når Oppfølgingsspillet er ferdig.",
      /** Story 9.10: the current Quiz step after the Faglærer took out every question the
       * Student's last attempt got wrong. [ASSUMPTION] */
      quizChanged: "pågår, quizen er endret",
      /** Story 9.11: the current Debrief step while a Group debrief of the Student's game is under
       * way that they have not joined; its link leads there. [ASSUMPTION] */
      groupOpen: "pågår, Gruppedebriefen er i gang",
      /** Story 10.3: the current Replay step after the Student's Testfrist with no Replay
       * started; it is not done. [ASSUMPTION] */
      replayClosed: "ikke gjort, Testfristen er ute",
      /** Story 10.6: the current Replay step once a started Replay was closed at the Testfrist
       * unfinished. [ASSUMPTION] */
      replayClosedUnfinished: "stengt ved Testfristen, ikke fullført",
      /** Story 11.11: the current Individual test step after the Student's Testfrist while it is
       * not handed in: never opened, or opened and waiting for the sweep (about a minute), after
       * which it turns done. [ASSUMPTION] The Replay's words. */
      testClosed: "ikke gjort, Testfristen er ute",
      /** Story 13.1 (FR-17, UX-DR29): in an Obligatorisk Klasseøkt, a done step that does not
       * count for the requirement says why, never with a number of Uker or a share (FR-14). Only
       * these three steps have a rule beyond being done. [ASSUMPTION] draft copy. */
      notCounted: {
        class_game: "ferdig, men du bestilte selv for sjelden",
        debrief: "ferdig, men Forklaringen er for kort",
        test: "levert, men en del mangler svar",
      } as Partial<Record<string, string>>,
      /** Story 13.3 (FR-17, UX-DR54): a step whose status a Faglærer corrected, marked so; the
       * Student never sees the reason. [ASSUMPTION] draft copy. */
      corrected: (counts: boolean) => (counts ? "gjort, rettet av faglærer" : "ikke gjort, rettet av faglærer"),
      /** Story 13.1 (FR-17): one line under Stegene in an Obligatorisk Klasseøkt, from the
       * Completion status. Neutral, so it stays true after the Testfrist. [ASSUMPTION] */
      requirement: {
        met: "Kravet er oppfylt.",
        notMet: "Kravet er ikke oppfylt.",
      },
      /** Story 10.4 (UX-DR64, EXPERIENCE.md → Replay in progress): the current Replay step while
       * the Replay runs; its link leads to the play screen. The spine's line. */
      replayResume: (week: number) => `Fortsett Replay, Uke ${week}.`,
      /** Story 10.3 (FR-48): the Replay on Hjem once the Debrief quiz is passed. «Replay» is the
       * spine's; the rest is [ASSUMPTION] draft copy for the founder's review. */
      replay: {
        /** «Replay · Du er Grossist», once started. */
        title: (role: string) => `Replay · Du er ${role}`,
        heading: "Replay",
        /** The consequence, above «Start Replay», before it is pressed. */
        consequence: "Du spiller én runde alene, i samme Rolle, mot tre KI-spillere. Etterspørselen er en annen enn i Klassespillet.",
        start: "Start Replay",
        /** Story 10.4: the way to the running Replay, at its open Uke; the spine's line as a
         * button label, without the full stop. */
        resume: (week: number) => `Fortsett Replay, Uke ${week}`,
        /** Story 10.5: the finished Replay, read again on its own screen. [ASSUMPTION] */
        view: "Se Replay",
        /** Story 10.6: a Replay closed at the Testfrist unfinished, on Hjem. [ASSUMPTION] */
        closed: "Replay ble stengt ved Testfristen og er ikke fullført.",
        failed: "Replay ble ikke startet. Prøv igjen.",
        errors: {
          quiz_required: "Bestå Debrief-quizen først.",
          test_deadline_passed: "Testfristen er ute. Replay kan ikke startes.",
        },
      },
      /** Story 13.4 (FR-17, EXPERIENCE.md → Fullføringsretting): the Oppfølgingsspill a Faglærer
       * gave the Student. «Oppfølgingsspill» is the spine's; the rest is [ASSUMPTION] draft copy. */
      makeup: {
        /** «Oppfølgingsspill · Du er Grossist», above its Setene. */
        title: (role: string) => `Oppfølgingsspill · Du er ${role}`,
        /** The Spillkort's title while it runs (UX-DR28). */
        card: "Oppfølgingsspill",
      },
      nextDeadline: "Neste frist",
      /** «Spillfrist ti. 8. des.» */
      deadline: (kind: string, day: string) => `${kind} ${day}`,
      labHour: "Labtime",
      /** «to. 26. nov. 14:15, Datalab A2». */
      labHourItem: (day: string, time: string, place: string) => `${day} ${time}, ${place}`,
      obligatory: "Obligatorisk",
      /** Story 6.2: Hjem's primary button to the briefing, until the Starting task is done. The
       * story's draft. [ASSUMPTION] */
      readRules: "Les reglene",
      /** Story 6.2: the briefing's Lenke afterwards, named by its title. */
      rulesLink: "Regler før første ordre",
      /** A finished game on Hjem (Story 6.18). [ASSUMPTION] draft copy: the spine names no
       * Hjem string for it; the Lenke leads to «Spillet er ferdig». */
      finished: "Spillet er ferdig.",
      /** Story 8.14 (FR-38) [ASSUMPTION] draft copy: the Play deadline playout has taken the game
       * over and AI players play it to the end. No blame, and never how many Uker are left. */
      playingOut: "Spillfristen er nådd. KI-spillere spiller spillet ferdig.",
      /** [ASSUMPTION] */
      toResult: "Se kjedens totalkostnad",
      /** Spillkort (Story 6.17, UX-DR28, EXPERIENCE.md → Spillkort, State Patterns → Student game).
       * «Spillet venter på deg», «Totalkostnad 68,00 kr» and «Netto lager −13 i Uke 11.» are the
       * spine's; `ordered` and `region` are [ASSUMPTION] draft copy: EXPERIENCE.md has no title for
       * a game that waits for others. */
      card: {
        waitsForYou: "Spillet venter på deg",
        /** [ASSUMPTION] The Student has ordered this Uke; the game waits for the others. */
        ordered: "Du har bestilt",
        week: (week: number) => `Uke ${week}`,
        total: (amount: string) => `Totalkostnad ${amount}`,
        /** Read in place of the mini graph, which is hidden from screen readers. */
        net: (value: string, week: number) => `Netto lager ${value} i Uke ${week}.`,
        /** The mini table's scroll region. [ASSUMPTION] */
        region: (number: number | null) => `Graf og tabell, ${gameName(number)}`,
      },
    },
  },

  /** The Lecturer's Classes (Epic 4). «Klassene dine», «Ny Klasse», «Lag Klasse», «Navn» and
   * «Emnekode» are EXPERIENCE.md's and the mockups' own; the rest is [ASSUMPTION] Story 4.1. */
  classes: {
    home: {
      title: "Klassene dine",
      empty: "Du har ingen Klasser ennå. En Klasse samler studentene dine og spillene deres.",
      newClass: "Ny Klasse",
      /** A Class on the list: «class-of-1994, IBE160». */
      label: (name: string, courseCode: string | null) => (courseCode ? `${name}, ${courseCode}` : name),
      waiting: "Venter",
      deadline: "Neste frist",
      nothingWaiting: "Ingenting venter ennå.",
      noDeadline: "Ingen frist ennå.",
      /** The Roster count beside each Class (Story 4.4, UX-DR56). [ASSUMPTION] */
      rosterCount: (count: number) =>
        count === 0 ? "Ingen på Klasselista" : `${count} ${count === 1 ? "adresse" : "adresser"} på Klasselista`,
    },
    create: {
      title: "Lag Klasse",
      lead: "Du blir eier av Klassen. Studentene legger du til etterpå.",
      name: "Navn",
      institution: "Institusjon",
      choose: "Velg Institusjon",
      noInstitutions: "Ingen Institusjoner ennå. Be en Admin opprette en.",
      courseCode: "Emnekode (valgfri)",
      submit: "Lag Klasse",
      failed: "Klassen ble ikke laget. Prøv igjen.",
    },
    errors: {
      name_empty: "Skriv navnet på Klassen.",
      name_too_long: "Navnet kan ha høyst 200 tegn.",
      name_invalid: "Navnet kan ikke inneholde kontrolltegn.",
      institution_missing: "Velg en Institusjon.",
      institution_unknown: "Institusjonen finnes ikke lenger. Velg en annen.",
      course_code_too_long: "Emnekoden kan ha høyst 50 tegn.",
      course_code_invalid: "Emnekoden kan ikke inneholde kontrolltegn.",
    },
    page: {
      /** The line under the Class's name: «IBE160 · Demohøgskolen». */
      facts: (courseCode: string | null, institution: string | null) =>
        [courseCode, institution].filter(Boolean).join(" · "),
      /** The Lenke to the Class's staff, for its Faglærere (Story 4.9). */
      staff: "Faglærere og assistenter",
      /** Above the Roster an Assistant lecturer reads (Story 4.9). [ASSUMPTION] */
      assistantLead: "Du er Assistent i Klassen. Du ser Klasselista, men Faglærerne endrer den.",
    },
    /** Archiving a Class (Story 4.10, FR-6, UX-DR56). [ASSUMPTION] draft copy: EXPERIENCE.md asks
     * only that the button states the consequence and that archived Classes are marked in text. */
    archive: {
      open: "Arkiver Klassen",
      title: "Arkiver Klassen",
      // [ASSUMPTION] Issue #93: the panel's own title, not the opener's words again.
      panelTitle: "Vil du arkivere Klassen?",
      /** The consequence, above the button, before it is pressed. */
      consequence:
        "Klassen blir skrivebeskyttet: Klasselista, Invitasjonene og Faglærere og assistenter kan ikke endres etterpå. Invitasjoner som ikke er brukt, slutter å virke. Klassen beholdes til oppbevaringstiden er ute, og det kan ikke angres.",
      submit: "Arkiver nå",
      cancel: "Avbryt",
      saving: "Arkiverer …",
      failed: "Klassen ble ikke arkivert. Prøv igjen.",
      /** The notice on an archived Class's page. */
      notice: "Klassen er arkivert. Den kan ikke endres, og den beholdes til oppbevaringstiden er ute.",
      /** Any action refused because the Class was archived meanwhile (`class_archived`). */
      refused: "Klassen er arkivert og kan ikke endres.",
      /** The Lærerhjem: archived Classes under their own heading, each marked in text. */
      homeTitle: "Arkiverte Klasser",
      marker: "Arkivert",
      noActive: "Ingen aktive Klasser.",
    },
    /** «Faglærere og assistenter» (Story 4.9, FR-10, UX-DR56). The title, «Legg til Faglærer»,
     * «Inviter Assistent» and «Assistenten får tilgang bare til denne Klassen.» are EXPERIENCE.md's
     * own; the rest is [ASSUMPTION] draft copy. */
    staff: {
      title: "Faglærere og assistenter",
      lecturers: "Faglærere",
      assistants: "Assistenter",
      lecturersLead: "Faglærerne eier Klassen sammen og har de samme rettighetene.",
      noAssistants: "Ingen Assistenter ennå.",
      addLecturer: "Legg til Faglærer",
      addLecturerTitle: "Legg til en Faglærer",
      addLecturerLead: "Personen må ha en konto med Faglærer-rollen. Klassen kommer på Lærerhjemmet deres.",
      // [ASSUMPTION] Issue #92: not the opener's own words, which stand beside it.
      addLecturerSubmit: "Legg til i Klassen",
      inviteAssistant: "Inviter Assistent",
      inviteAssistantTitle: "Inviter en Assistent",
      assistantScope: "Assistenten får tilgang bare til denne Klassen.",
      // [ASSUMPTION] Issue #92: the form's lead; the scope line already stands under «Assistenter».
      inviteAssistantLead: "Personen får en e-post med en lenke som virker i 14 dager.",
      inviteAssistantSubmit: "Send Invitasjon",
      email: "E-post",
      cancel: "Avbryt",
      saving: "Lagrer …",
      /** Each person's status, in text. */
      active: "Aktiv",
      invited: (lastDay: string) => `Invitert, gyldig til og med ${lastDay}`,
      expired: "Invitasjonen er utløpt",
      remove: "Fjern",
      removeFor: (who: string) => `Fjern ${who}`,
      removeTitle: (who: string) => `Fjern ${who} fra Klassen`,
      // [ASSUMPTION] Issue #92: someone only invited is not in the Class yet.
      withdrawTitle: (who: string) => `Trekk tilbake Invitasjonen til ${who}`,
      /** The consequence, above the button, before it is pressed. */
      removeLecturer: (who: string) => `${who} mister tilgangen til Klassen fra neste side de åpner. Kontoen beholdes.`,
      removeSelf: "Du mister tilgangen til Klassen. De andre Faglærerne beholder den.",
      removeAssistant: (who: string) => `${who} mister tilgangen til Klassen fra neste side de åpner. Kontoen beholdes.`,
      withdraw: (who: string) => `Invitasjonen til ${who} slutter å virke.`,
      withdrawExpired: (who: string) => `Den utløpte Invitasjonen til ${who} fjernes fra lista.`,
      removeSubmit: "Fjern fra Klassen",
      withdrawSubmit: "Trekk tilbake Invitasjonen",
      /** The result lines. */
      lecturerAdded: (who: string) => `${who} er Faglærer i Klassen.`,
      assistantInvited: (address: string) => `Invitasjonen er sendt til ${address}.`,
      removed: (who: string) => `${who} er fjernet fra Klassen.`,
      withdrawn: (address: string) => `Invitasjonen til ${address} er trukket tilbake.`,
      gone: "Personen står ikke lenger på lista.",
      /** Beside a refused field, and the last-owner refusal. */
      notLecturer: "Adressen tilhører ingen Faglærer. Be Admin gi personen Faglærer-rollen.",
      alreadyStaff: "Personen er allerede med i Klassen.",
      lastOwner: "Klassen må ha minst én Faglærer. Legg til en annen Faglærer først.",
      failed: "Det ble ikke lagret. Prøv igjen.",
      removeFailed: "Personen ble ikke fjernet. Prøv igjen.",
      loadFailed: "Lista kunne ikke hentes.",
    },
    /** What became of the Invitations on the Class page (Story 4.6, FR-8, NFR-10). [ASSUMPTION]
     * draft copy. */
    invitations: {
      title: "Invitasjoner",
      /** The four counts, label over figure. */
      sent: "Sendt",
      bounced: "Kom ikke fram",
      accepted: "Akseptert",
      expired: "Utløpt",
      bouncedTitle: "Kom ikke fram",
      bouncedLead: "E-posten nådde ikke disse adressene.",
      /** A bounced address's registration status, always in text (NFR-10). */
      bounceStatus: (bounceClass: "hard" | "soft") =>
        bounceClass === "hard" ? "Kom ikke fram, permanent feil" : "Kom ikke fram, midlertidig feil",
      failed: "Tallene for Invitasjonene kunne ikke hentes.",
    },
    /** «Status etter utsending» on the Class page (Story 4.7, FR-9, NFR-10, UX-DR47). The title,
     * «Registrert», «Manuelt», «Uregistrert» and «Send påminnelse til N» are EXPERIENCE.md's own;
     * the rest is [ASSUMPTION] draft copy. */
    registration: {
      title: "Status etter utsending",
      /** The totals, in text beside the bar's keys: «Registrert 238». */
      registered: "Registrert",
      manual: "Manuelt",
      unregistered: "Uregistrert",
      total: (label: string, count: number) => `${label} ${count}`,
      remindAll: (count: number) => `Send påminnelse til ${count}`,
      /** The confirm panel the link opens. */
      confirmTitle: "Send påminnelse",
      confirmLead: "Alle som ikke har registrert seg, får en ny Invitasjon. Den gamle lenken slutter å virke.",
      confirmLeft: (count: number) =>
        `${count} ${count === 1 ? "adresse" : "adresser"} med permanent feil får ingen påminnelse.`,
      confirm: (count: number) => `Send ${count} ${count === 1 ? "påminnelse" : "påminnelser"}`,
      cancel: "Avbryt",
      sending: "Sender …",
      /** The result line: «4 påminnelser sendt. Gyldige til og med 3. desember.» */
      sent: (count: number, lastDay: string) =>
        count === 0
          ? "Ingen påminnelser sendt."
          : `${count} ${count === 1 ? "påminnelse sendt. Gyldig" : "påminnelser sendt. Gyldige"} til og med ${lastDay}.`,
      resent: (address: string, lastDay: string) => `Ny Invitasjon sendt til ${address}. Gyldig til og med ${lastDay}.`,
      /** The hard-bounced addresses a reminder left out, named so they can be corrected. */
      leftOut: "Ikke sendt, fordi e-posten ikke kom fram (permanent feil):",
      sendFailed: "Påminnelsene ble ikke sendt. Prøv igjen.",
      nothingToSend: "Ingen av adressene trenger en påminnelse nå.",
      failed: "Statusen for Klasselista kunne ikke hentes.",
      /** The list under the totals. */
      listTitle: "Adresser",
      filter: "Vis",
      filterAll: "Alle statuser",
      search: "Søk etter adresse",
      shown: (shown: number, total: number) => `Viser ${shown} av ${total} adresser.`,
      noMatch: "Ingen adresser passer til søket.",
      resend: "Send ny Invitasjon",
      resendFor: (address: string) => `Send ny Invitasjon til ${address}`,
      // [ASSUMPTION] Issue #91: a row «Ikke invitert ennå» gets its first Invitation, never a «ny».
      invite: "Send Invitasjon",
      inviteFor: (address: string) => `Send Invitasjon til ${address}`,
      invitedOne: (address: string, lastDay: string) => `Invitasjon sendt til ${address}. Gyldig til og med ${lastDay}.`,
      /** Each status in text, never colour alone (FR-9, NFR-10). */
      status: {
        registered: "Registrert",
        registered_manually: "Registrert manuelt",
        renewal_requested: "Ba om ny Invitasjon",
        bounced: "Kom ikke fram",
        invited: "Invitert",
        unregistered: "Uregistrert, Invitasjonen er utløpt",
        // Story 4.8: added by hand, no Invitation sent yet. [ASSUMPTION]
        not_invited: "Ikke invitert ennå",
      },
      invitedUntil: (lastDay: string) => `Invitert, gyldig til og med ${lastDay}`,
    },
    /** Manual registration and single addresses (Story 4.8, FR-7, FR-9, UX-DR47). «Registrer
     * manuelt» is EXPERIENCE.md's own; the rest is [ASSUMPTION] draft copy. */
    entries: {
      add: "Legg til adresse",
      addTitle: "Legg til én adresse",
      addLead: "Adressen kommer på Klasselista uten Invitasjon. Den får sin første med neste påminnelse.",
      addSubmit: "Legg til",
      manual: "Registrer manuelt",
      manualFor: (address: string) => `Registrer manuelt, ${address}`,
      manualTitle: "Registrer en student manuelt",
      manualLead:
        "Studenten kommer inn i Klassen med en gang og får en e-post. Har adressen ingen konto, følger det med en lenke for å velge passord.",
      email: "E-post",
      name: "Navn",
      nameHint: "Brukes bare når adressen ikke har konto fra før.",
      manualSubmit: "Registrer studenten",
      cancel: "Avbryt",
      saving: "Lagrer …",
      remove: "Fjern",
      removeFor: (address: string) => `Fjern ${address}`,
      removeTitle: (address: string) => `Fjern ${address} fra Klasselista`,
      /** The consequence, above the button, before it is pressed. */
      removeRegistered: (address: string) =>
        `${address} mister tilgangen til Klassen. Kontoen og andre Klasser beholdes.`,
      removeWaiting: (address: string) =>
        `Invitasjonen til ${address} slutter å virke, og adressen får ingen påminnelser.`,
      removeNotInvited: (address: string) => `${address} har ikke fått noen Invitasjon og får ingen påminnelser.`,
      removeSubmit: "Fjern fra Klasselista",
      /** The result lines. */
      added: (address: string) => `${address} er lagt til. Ikke invitert ennå.`,
      restored: (address: string) => `${address} står på Klasselista igjen.`,
      registered: (address: string) => `${address} er registrert manuelt og får en e-post.`,
      removed: (address: string) => `${address} er fjernet fra Klasselista.`,
      /** Beside a refused field. */
      alreadyRegistered: "Adressen er allerede registrert i Klassen.",
      emailTooLong: "Adressen er for lang.",
      nameEmpty: "Skriv navnet til studenten.",
      nameTooLong: "Navnet kan ha høyst 200 tegn.",
      failed: "Det ble ikke lagret. Prøv igjen.",
      removeFailed: "Adressen ble ikke fjernet. Prøv igjen.",
      gone: "Adressen står ikke lenger på Klasselista.",
    },
    /** The Roster upload on the Class page (Story 4.2, FR-7, UX-DR47). «Velg fil», «Lim inn
     * adresser i stedet», «250 rader lest», «Bytt fil», «E-postkolonne», the reason and the
     * unreadable line are EXPERIENCE.md's and DESIGN.md's own; the rest is [ASSUMPTION] Story 4.2. */
    roster: {
      title: "Klasseliste",
      lead: "Klasselisten kommer fra Canvas-eksporten din. Ingenting sendes før du trykker send.",
      fileLabel: "Canvas-eksport",
      chooseFile: "Velg fil",
      accepts: "Excel (.xlsx) eller CSV (.csv), slik Canvas eksporterer den.",
      pasteInstead: "Lim inn adresser i stedet",
      fileInstead: "Velg fil i stedet",
      pasteLabel: "Adresser",
      pasteHint: "Én adresse per linje, eller skilt med komma eller semikolon.",
      reading: "Leser fila …",
      rowsRead: (rows: number) => `${rows} ${rows === 1 ? "rad" : "rader"} lest`,
      changeFile: "Bytt fil",
      unreadable: "Filen kunne ikke leses. Bruk .xlsx eller .csv, eller lim inn adressene.",
      uploadFailed: "Fila ble ikke lastet opp. Prøv igjen.",
      changeFailed: "Fila ble ikke fjernet. Prøv igjen.",
      columnFailed: "Kolonnen ble ikke byttet. Prøv igjen.",
      emailColumn: "E-postkolonne",
      chooseColumn: "Velg kolonne",
      /** A column in the selector: «Kolonne C, E-post», or «Kolonne C» with no header. */
      column: (letter: string, header: string) => (header ? `Kolonne ${letter}, ${header}` : `Kolonne ${letter}`),
      /** Why the preselected column was chosen, «Valgt fordi alle rader unntatt fire er gyldige
       * adresser.», counting the same rows as «Ugyldige rader: 4 av 250» (Issue #86): repeats and
       * addresses already on the Klasseliste are not valid either. */
      suggested: (valid: number, rows: number) =>
        valid === rows
          ? "Valgt fordi alle rader er gyldige adresser."
          : valid * 2 >= rows
            ? `Valgt fordi alle rader unntatt ${countWord(rows - valid)} er gyldige adresser.`
            : `Valgt fordi ${valid} av ${rows} rader er gyldige adresser.`,
      /** A column the Lecturer chose themself, evaluated again by the api; `matching` counts
       * the cells that look like addresses at all. */
      chosen: (matching: number, valid: number, rows: number) =>
        matching === 0
          ? "Ingen rader i denne kolonnen ser ut som adresser."
          : `${valid} av ${rows} rader er gyldige adresser.`,
      noEmailColumn:
        "Ingen kolonne i fila ser ut som e-postadresser. Velg kolonnen selv, eller lim inn adressene i stedet.",
      preview: "Forhåndsvisning av fila",
      previewRow: "Rad",
      previewNote: (shown: number, rows: number) => `De første ${shown} av ${rows} radene.`,
      /** Read by screen readers after the chosen column's header in the preview; on screen the
       * column's tint marks it (Issue #85). */
      previewChosen: "valgt som e-postkolonne",
      // Story 4.3 (FR-7, UX-DR47). [ASSUMPTION] draft copy except the heading, the reasons the
      // UX spine names, «Registrer manuelt», the note and «Send N Invitasjoner».
      invalidTitle: (invalid: number, rows: number) => `Ugyldige rader: ${invalid} av ${rows}`,
      invalidRow: "Rad",
      /** The value column of the invalid-row list names the chosen column (Issue #86). */
      invalidValue: (header: string, letter: string) => header || `Kolonne ${letter}`,
      invalidReason: "Hva er galt",
      /** For pasted addresses, which have no file rows: their place in the text. */
      invalidPlace: "Nr.",
      invalidPasted: "Innlimt verdi",
      invalidShown: (shown: number, invalid: number) => `Viser de første ${shown} av ${invalid} ugyldige radene.`,
      /** Why a row gets no Invitation, always in text (NFR-6). */
      reasons: {
        empty: "Tom celle",
        whitespace: "Mellomrom i adressen",
        missing_at: "Mangler @",
        two_at: "To @",
        missing_name: "Mangler navn før @",
        missing_domain: "Domene mangler",
      },
      duplicate: (firstRow: number) => `Dublett av rad ${firstRow}`,
      /** Story 4.4 (FR-7). [ASSUMPTION] */
      onRoster: "Står allerede på Klasselista",
      registerManually: "Registrer manuelt",
      invalidNote: "Ugyldige rader får ingen e-post før de er rettet.",
      send: (valid: number) => `Send ${valid} ${valid === 1 ? "Invitasjon" : "Invitasjoner"}`,
      noValid: "Ingen gyldige adresser å invitere.",
      // [ASSUMPTION] Issue #91: a removed, registered Student sent again comes back with access and
      // gets no Invitation, so «Send N» leaves them out and this line names them.
      restoredNote: (count: number) =>
        count === 1
          ? "Én adresse tilhører en registrert student som var fjernet. Studenten får tilgang igjen uten ny Invitasjon."
          : `${count} adresser tilhører registrerte studenter som var fjernet. De får tilgang igjen uten ny Invitasjon.`,
      // [ASSUMPTION] Issue #91: the button when every valid row is such a Student.
      restoreOnly: "Legg tilbake på Klasselista",
      pasteContinue: "Fortsett",
      pasted: "Innlimte adresser",
      addressesRead: (count: number) => `${count} ${count === 1 ? "adresse" : "adresser"} lest`,
      startOver: "Start på nytt",
      pasteTooLong: "Teksten er for lang for én klasseliste. Lim inn færre adresser.",
      pasteFailed: "Adressene ble ikke lest inn. Prøv igjen.",
      // Story 4.4 (FR-8). [ASSUMPTION] draft copy except «Send N Invitasjoner».
      /** Under the lead on the Class page once the Roster has addresses. */
      onRosterCount: (count: number) => `${count} ${count === 1 ? "adresse står" : "adresser står"} på Klasselista.`,
      validDays: "Gyldig i antall dager",
      validDaysHint: (min: number, max: number) => `Mellom ${min} og ${max} dager.`,
      validDaysError: (min: number, max: number) => `Velg et helt antall dager mellom ${min} og ${max}.`,
      /** The result line after sending: «246 Invitasjoner sendt. Gyldige til og med 3. desember.» */
      sent: (count: number, lastDay: string) =>
        count === 0
          ? // [ASSUMPTION] Issue #91: only registered Students were put back.
            "Klasselista er oppdatert. Ingen nye Invitasjoner sendt."
          : `${count} ${count === 1 ? "Invitasjon sendt. Gyldig" : "Invitasjoner sendt. Gyldige"} til og med ${lastDay}.`,
      sending: "Sender …",
      sendFailed: "Invitasjonene ble ikke sendt. Prøv igjen.",
      sendGone: "Klasselista er endret siden du lastet den. Se over og send igjen.",
      /** After a refused send whose staging has no valid row left; the refetched staging then
       * shows «Ingen gyldige adresser å invitere.» under the button, so this line says why. */
      nothingToSend: "Klasselista er endret siden du lastet den. Ingen av adressene kan inviteres nå.",
      months: [
        "januar",
        "februar",
        "mars",
        "april",
        "mai",
        "juni",
        "juli",
        "august",
        "september",
        "oktober",
        "november",
        "desember",
      ],
    },
  },

  /** The Klasseøkt (Story 5.1, FR-11, UX-DR48). The page title, «Alt er fylt ut med
   * standardene.», «Spillinnstillinger: Klassisk», the delay-sources line, «Kjeden ved start»,
   * «Varer mot høyre, ordre mot venstre», «Lagre Klasseøkt», «Du kan lagre uten å endre noe.»,
   * the setting labels and the KI-modus and Debrief-modus names are EXPERIENCE.md's and mockup
   * 03's own; the rest is [ASSUMPTION] draft copy. */
  sessions: {
    title: (className: string) => `Klasseøkt for ${className}`,
    crumb: "Klasseøkt",
    defaults: "Alt er fylt ut med standardene.",
    settingsTitle: "Spillinnstillinger: Klassisk",
    // [ASSUMPTION] the heading once a setting differs from Classic (Story 5.3 adds its line).
    settingsTitleChanged: "Spillinnstillinger",
    delaySources: "Kildene er uenige om forsinkelsene. Dette er produktets standard, og du kan endre den.",
    settings: {
      startingInventory: "Startlager",
      supplyLine: "I hvert ledd ved start",
      orderDelay: "Ordreforsinkelse",
      shippingDelay: "Fraktforsinkelse",
      productionDelay: "Produksjonsforsinkelse",
      holdingCost: "Lagerkost",
      backorderCost: "Restordrekost",
      weeks: "Antall uker",
      demand: "Etterspørsel",
      // [ASSUMPTION] Story 5.4: the seed of a pattern that draws, under «Etterspørsel».
      seed: "Frø",
      guidedWeeks: "Veiledede uker",
      inactivityLimit: "Inaktivitetsgrense",
      // [ASSUMPTION] Story 5.3: the two settings the list did not show before.
      startingBacklog: "Startrestordre",
      maxOrder: "Største ordre",
      // [ASSUMPTION] Story 5.15 (cut list, FEATURE_CAPACITY): the most a Role can ship per Week.
      capacity: "Kapasitet",
      // [ASSUMPTION] Story 5.16 (cut list, FEATURE_INFO_VISIBILITY): EXPERIENCE.md's draft name.
      infoVisibility: "Synlige naboer",
    },
    /** Changing the Game settings (Story 5.3, FR-12, UX-DR48). [ASSUMPTION] draft copy. The api
     * judges every value; these lines only word its codes. Numbers arrive formatted. */
    edit: {
      open: "Endre spillinnstillinger",
      cancel: "Avbryt endringene",
      // Under the field: one value holds for all four Roles.
      perRole: "Gjelder hvert ledd.",
      costHint: "Kroner per enhet per uke, med komma.",
      guidedHint: "Antall uker fra Uke 1 med veiledning.",
      // Story 5.7 (EXPERIENCE.md → Klasseøkt, «Ventetid før KI tar over», UX-DR49).
      inactivityHint: "Minst 20 timer. Kortere ventetid kan bare gjelde spill som er i rommet i en Labtime.",
      inactivityError: "Skriv et helt antall timer, 20 eller mer.",
      refused: "Spillinnstillingene ble ikke lagret. Se feltene.",
      errors: {
        outOfRange: (min: string, max: string) => `Må være fra ${min} til ${max}.`,
        // Story 10.2: an own Replay scenario's range typed the wrong way round, under its second field.
        rangeInverted: (low: string) => `Må være ${low} eller mer, ikke lavere enn det første tallet.`,
        wholeNumber: (min: string, max: string) => `Skriv et helt tall fra ${min} til ${max}.`,
        amount: (min: string, max: string) => `Skriv et beløp fra ${min} til ${max}, med komma.`,
        decimals: (places: number, min: string, max: string) =>
          `Bruk høyst ${places} desimaler, fra ${min} til ${max}.`,
        guidedBeforeChange: (min: string, max: string) =>
          `Veiledningen må slutte før etterspørselen endres. Velg fra ${min} til ${max}.`,
        guidedLeaveWeeks: (min: string, max: string) =>
          `Det må være uker igjen å spille etter veiledningen. Velg fra ${min} til ${max}.`,
        inventoryAndBacklog: "Et ledd kan ikke starte med både lager og restordre. Sett ett av dem til 0.",
        demandChangeOutside: (min: string, max: string) =>
          `Etterspørselen må endres i en uke fra ${min} til ${max}. Velg en tidligere uke eller flere uker i Antall uker.`,
        // [ASSUMPTION] Story 5.4: the Demand pattern's own rules.
        fixedLength: (count: string) => `Skriv ett helt tall per uke, ${count} tall i alt.`,
        seedRequired: "Skriv et frø, et helt tall.",
        pattern: "Velg et mønster og fyll ut feltene.",
        notEditable: "Denne innstillingen kan ikke endres her.",
        other: "Verdien er ikke tillatt.",
      },
      /** Never blocking; the word «Advarsel» carries it, not the colour. */
      warnings: {
        supplyLine: (supply: string, start: string) =>
          `Advarsel: ${supply} i hvert ledd er ikke det samme som etterspørselen ved start (${start}), så kjeden starter ikke i balanse.`,
        backorder: (backorder: string, holding: string) =>
          `Advarsel: Restordrekost (${backorder}) er ikke høyere enn Lagerkost (${holding}). Da koster det ikke mer å gå tom enn å ha varer på lager.`,
        maxOrder: (max: string, threshold: string, peak: string) =>
          `Advarsel: Største ordre (${max}) er under ${threshold}. Med etterspørsel opp til ${peak} kan grensen stoppe vanlige ordre.`,
        weeks: (arrival: string, weeks: string) =>
          `Advarsel: Endringen i etterspørselen når Detaljisten tidligst i Uke ${arrival}, etter siste uke (${weeks}).`,
        // [ASSUMPTION] Story 5.15: one line however many Roles are capped.
        capacity: (capacity: string, peak: string) =>
          `Advarsel: Kapasiteten (${capacity} per uke) er under den høyeste etterspørselen (${peak}). Et ledd med kapasitet holder ikke følge når etterspørselen er høyest.`,
        other: "Advarsel: Uvanlig verdi.",
      },
      /** A shipping capacity (Story 5.15, cut list, FEATURE_CAPACITY, FR-12). [ASSUMPTION] draft
       * copy. The api judges the value; the briefing wording is Story 6.22's. */
      capacity: {
        legend: "Kapasitet",
        off: "Nei, ingen grense",
        on: "Ja, begrens hvor mye som kan sendes per uke",
        scope: "Gjelder",
        all: "Alle ledd",
        one: "Ett ledd",
        role: "Ledd",
        units: "Enheter per uke",
        unitsHint: "Et helt tall over 0.",
        help: "Et ledd med kapasitet kan ha lager og restordre samtidig. Studentene får vite kapasiteten i briefingen.",
        disabled: "Kapasitet er slått av i denne installasjonen.",
      },
      /** Information visibility (Story 5.16, cut list, FEATURE_INFO_VISIBILITY, FR-83, UX-DR12).
       * [ASSUMPTION] draft copy. Showing the numbers on the play screen is Story 6.21's. */
      infoVisibility: {
        legend: "Synlige naboer",
        upstream: "Leddet oppstrøms",
        downstream: "Leddet nedstrøms",
        upstreamOn: "Ja, vis lager og restordre hos leddet du bestiller fra",
        downstreamOn: "Ja, vis lager og restordre hos leddet som bestiller fra deg",
        off: "Nei",
        help:
          "Gjelder alle Klassespill i Klasseøkten, også KI-spillerne. Tallene er naboleddets lager og restordre slik de står i uken. " +
          "Fabrikken har ingen nabo oppstrøms, og Detaljisten ingen nedstrøms. Det er ikke vist at innstillingen gir bedre læring eller lavere kost.",
        disabled: "Synlige naboer er slått av i denne installasjonen.",
      },
      // [ASSUMPTION] Story 5.16: a save refused because a cut-list setting is switched off.
      featureDisabled: "En av innstillingene er slått av i denne installasjonen. Ingenting ble lagret.",
      // [ASSUMPTION] GitHub issue 114: the save line when the reason stands at the field.
      notSaved: "Ikke lagret.",
      /** The Demand pattern and its seed (Story 5.4, FR-13). [ASSUMPTION] draft copy. */
      demand: {
        legend: "Etterspørsel",
        pattern: "Mønster",
        kinds: {
          fixed: "Fast serie",
          step: "Trinn",
          random: "Tilfeldig",
          "step+noise": "Trinn med tilfeldig variasjon",
        },
        values: "Etterspørsel per uke",
        valuesHint: "Ett helt tall per uke fra Uke 1, skilt med mellomrom eller komma og mellomrom.",
        start: "Startnivå",
        newLevel: "Nytt nivå",
        changeWeek: "Endres fra uke",
        mean: "Snitt",
        spread: "Spredning",
        spreadHint: "Hver uke trekkes et helt tall opp til så mye over eller under, aldri under 0.",
        seed: "Frø",
        seedHint:
          "Samme frø gir samme etterspørsel i alle Klassespill. Serveren trakk et frø da Klasseøkten ble laget; du kan beholde det eller skrive et annet helt tall.",
      },
      /** The series Week by Week, for the Lecturer (Story 5.4). [ASSUMPTION] */
      series: {
        show: "Vis etterspørselen uke for uke",
        hide: "Skjul etterspørselen uke for uke",
        caption: "Etterspørselen uke for uke",
        week: "Uke",
        demand: "Etterspørsel",
        loading: "Henter etterspørselen …",
        failed: "Etterspørselen kunne ikke hentes. Prøv igjen.",
      },
      /** Shown once a setting differs from Classic (FR-12), from the values the api returned. */
      calibrated: (v: {
        inventory: string;
        slot: string;
        order: string;
        shipping: string;
        production: string;
        holding: string;
        backorder: string;
        weeks: string;
      }) =>
        `Debrief-oppgavene og kontrollen av KI-spillerne er kalibrert for Klassisk: Startlager ${v.inventory}, ${v.slot} i hvert ledd, ` +
        `forsinkelser ${v.order}, ${v.shipping} og ${v.production} uker, Lagerkost ${v.holding}, Restordrekost ${v.backorder} og ${v.weeks} uker.`,
    },
    values: {
      units: (count: number) => `${count} ${count === 1 ? "enhet" : "enheter"}`,
      weeks: (count: number) => `${count} ${count === 1 ? "uke" : "uker"}`,
      /** A cost rate, decimal comma already applied: «0,50 per enhet per uke». */
      cost: (rate: string) => `${rate} per enhet per uke`,
      /** The step pattern: «4, så 8 fra Uke 5». */
      step: (start: number, next: number, week: number) => `${start}, så ${next} fra Uke ${week}`,
      // [ASSUMPTION] Story 5.4: the other Demand patterns in words.
      stepNoise: (start: number, next: number, week: number, spread: number) =>
        `${start}, så ${next} fra Uke ${week}, ± ${spread} tilfeldig`,
      random: (mean: number, spread: number) => `Tilfeldig, ${mean} ± ${spread}`,
      fixed: (weeks: number) => `Fast serie over ${weeks} ${weeks === 1 ? "uke" : "uker"}`,
      guidedWeeks: (count: number) => (count === 0 ? "Ingen" : count === 1 ? "1" : `1–${count}`),
      inactivityLimit: (hours: number) => `${hours} t, så KI overtar`,
      // [ASSUMPTION] Story 5.15: the capacity in the settings list.
      capacityNone: "Ingen",
      capacityAll: (units: number) => `${units} per uke for alle ledd`,
      capacityRoles: (units: string, roles: string) => `${units} per uke for ${roles}`,
      // [ASSUMPTION] Story 5.16: Information visibility in the settings list.
      infoVisibilityNone: "Av",
      infoVisibilityUpstream: "Leddet oppstrøms",
      infoVisibilityDownstream: "Leddet nedstrøms",
      infoVisibilityBoth: "Begge naboene",
    },
    chain: {
      title: "Kjeden ved start",
      caption: "Varer mot høyre, ordre mot venstre",
      customers: "Kundene",
      /** The demand in two short lines under «Kundene», as mockup 03 («4, så 8» / «fra Uke 5»,
       * Issue #98). [ASSUMPTION] the lines of the other patterns. */
      customerLines: {
        step: (start: number, next: number, week: number) => [`${start}, så ${next}`, `fra Uke ${week}`] as const,
        stepNoise: (start: number, next: number, week: number, spread: number) =>
          [`${start}, så ${next} ± ${spread}`, `fra Uke ${week}`] as const,
        random: (mean: number, spread: number) => [`${mean} ± ${spread}`, "tilfeldig"] as const,
        fixed: (weeks: number) => ["Fast serie", `${weeks} ${weeks === 1 ? "uke" : "uker"}`] as const,
      },
      inventory: (units: number) => `Lager ${units}`,
      // [ASSUMPTION] Story 5.15: under a capped Role in the diagram, and the sentence in its text.
      capped: (units: number) => `Maks ${units}`,
      cappedText: (role: string, units: number) => `${role} kan sende høyst ${units} per uke.`,
      delay: (weeks: number) => `${weeks} ${weeks === 1 ? "uke" : "uker"}`,
      /** The diagram's text: the same values as sentences, also read by screen readers. */
      text: (v: {
        roles: string;
        inventory: number;
        slot: number;
        shipping: number;
        production: number;
        order: number;
        demand: string;
      }) =>
        `${v.roles} starter med Lager ${v.inventory} hver. Hver boks på røret er ${v.slot} ${v.slot === 1 ? "enhet" : "enheter"}. ` +
        `Frakt mellom leddene tar ${v.shipping} ${v.shipping === 1 ? "uke" : "uker"}, og produksjon inn til Fabrikk tar ${v.production} ${v.production === 1 ? "uke" : "uker"}. ` +
        `Prikkene er ordre på vei, ${v.order} ${v.order === 1 ? "uke" : "uker"}. Kundenes etterspørsel: ${v.demand}. Studentene ser ikke kundene under spillet.`,
      /** «Fabrikk, Distributør, Grossist og Detaljist». */
      list: (names: readonly string[]) =>
        names.length < 2 ? names.join("") : `${names.slice(0, -1).join(", ")} og ${names[names.length - 1]}`,
    },
    choices: {
      aiMode: "KI-modus",
      llm: "LLM-spillere",
      ruleBased: "Regelbaserte spillere",
      debriefMode: "Debrief-modus",
      group: "Gruppedebrief",
      personal: "Personlig debrief",
      /** Story 9.2 (FR-42, UX-DR12): when the Debriefs open. [ASSUMPTION] draft copy. */
      debriefRelease: "Når Debriefen åpner",
      releaseOpen: "Når eget spill er ferdig",
      releaseHold: "Når alle spill er ferdige",
      releaseOpenHelp:
        "Studentene kan starte Debriefen så snart deres eget spill er ferdig. Da kan de fortelle om etterspørselen til Studenter som fortsatt spiller.",
      releaseHoldHelp: "Alle Debriefer åpner når det siste Klassespillet er ferdig.",
      /** Story 9.14 (FR-15, FR-44): the Debrief's AI text, a Bryter. [ASSUMPTION] draft copy. */
      debriefAiText: "KI-tekst i Debriefen",
      debriefAiTextOn: "På",
      debriefAiTextOff: "Av",
      debriefAiTextOnHelp:
        "En KI setter sammen en kort tekst om øyeblikkene til hver Student, merket som KI-generert. Tallene regnes alltid ut av koden.",
      debriefAiTextOffHelp: "Debriefen viser bare tekst som er regnet ut av koden. Ingen tekst går til en KI.",
      obligatory: "Obligatorisk",
      obligatoryYes: "Ja, står i emneplanen",
      // [ASSUMPTION]
      obligatoryNo: "Nei",
      // Mockup 03, under the Bryter while it is on (Story 5.7).
      obligatoryHelp: "Studentene ser at øvelsen er obligatorisk.",
      // [ASSUMPTION] draft copy of Story 5.7, not in the spine: the required share of Weeks.
      share: "Andel uker som kreves",
      shareHint: "Et helt tall fra 1 til 100 %.",
      shareError: "Skriv et helt tall fra 1 til 100.",
      shareValue: (percent: number) => `Andel uker som kreves: ${percent} %`,
      // [ASSUMPTION] the alert line of a save the api refused for the share or the Ventetid.
      valuesRefused: "Klasseøkten ble ikke lagret. Se feltene.",
      // [ASSUMPTION] FR-15: no model config is pinned as the default.
      llmUnavailable:
        "LLM-spillere kan ikke velges før en Admin har valgt en standardmodell. Til da får Klasseøkten regelbaserte spillere.",
      // Story 5.5 (EXPERIENCE.md → KI-modus setup).
      aiScope: "Gjelder alle KI-spillere i Klassespill og Replay.",
      // [ASSUMPTION] the disclosures with each AI player type's description (FR-33).
      aboutLlm: "Slik bestiller LLM-spillerne",
      aboutRuleBased: "Slik bestiller de regelbaserte spillerne",
      effortLevel: "Innsatsnivå",
      // [ASSUMPTION] a level whose config has no effect line and no measurement with figures.
      effectUnknown: "Virkningen på fart og kostnad er ikke målt ennå.",
      // [ASSUMPTION] the measured effect of a level: median time per Order, cost per game.
      effectMeasured: (seconds: string, cost: string) => `Ca. ${seconds} s per ordre, ${cost} USD per spill.`,
      effectSeconds: (seconds: string) => `Ca. ${seconds} s per ordre.`,
      effectCost: (cost: string) => `${cost} USD per spill.`,
      // [ASSUMPTION] AD-17: LLM players chosen, but the provider of the session's model has no key.
      providerUnavailable:
        "Klasseøkten kan ikke starte med LLM-spillere før KI-leverandøren er satt opp. Be en Admin ordne det før startdatoen, eller velg regelbaserte spillere.",
      // Mockup 03 for Gruppedebrief; [ASSUMPTION] for Personlig debrief.
      groupHelp: "De fire i spillet går gjennom det sammen.",
      personalHelp: "Hver student går gjennom det alene.",
      // [ASSUMPTION] the save of a level the model config no longer offers (`invalid_effort_level`).
      effortRefused: "Innsatsnivået kan ikke velges lenger. Last siden på nytt og velg et annet.",
    },
    /** The Klasseøkt's Replay scenario (Story 10.1, FR-49, FR-72): the default, described in
     * words; the drawn values stay hidden from the Students. [ASSUMPTION] draft copy. */
    replay: {
      title: "Replay-scenario",
      standard: "Standard",
      demand: "Etterspørsel",
      changeWeek: "Uke for endring",
      weeks: "Antall uker",
      guidedWeeks: "Veiledede uker",
      rest: "Resten",
      restValue: "Som Spillinnstillingene",
      none: "Ingen",
      stepDemand: (start: number, newLevel: number) => `${start}, deretter ${newLevel}`,
      randomDemand: (mean: number) => `Rundt ${mean}`,
      fixedDemand: "Serien i Spillinnstillingene, siste verdi videre",
      /** Appended to the demand once it varies: «4, deretter 8, ± 2 hver uke». */
      spread: (demand: string, spread: number) => `${demand}, ± ${spread} hver uke`,
      range: (minimum: number, maximum: number) => `${minimum} til ${maximum}`,
      weekRange: (minimum: number, maximum: number) => `Uke ${minimum} til ${maximum}`,
      week: (week: number) => `Uke ${week}`,
      /** Under the list: what is drawn per Student, by which values are ranges. */
      hiddenBoth:
        "Uka for endringen og antall uker trekkes for hver student og vises ikke for studentene. Hver student får sin egen etterspørsel, med samme nivåer som i Klassespillet.",
      hiddenWeeks:
        "Antall uker trekkes for hver student og vises ikke for studentene. Hver student får sin egen etterspørsel, med samme nivåer som i Klassespillet.",
      hiddenNone: "Hver student får sin egen etterspørsel, med samme nivåer som i Klassespillet.",
      /** Story 10.2 (FR-49, UX-DR12, UX-DR48): the own scenario. [ASSUMPTION] draft copy. */
      choice: "Scenario",
      own: "Eget scenario",
      choiceHelp: "Gjelder alle Replay i Klasseøkta. Valget tar effekt når du lagrer Klasseøkta.",
      ownLead: "Starter fra Spillinnstillingene. Endre det du vil; Replay bruker verdiene her.",
      weeksFrom: "Antall uker, minst",
      weeksTo: "Antall uker, høyst",
      changeWeekFrom: "Endres fra uke, tidligst",
      changeWeekTo: "Endres fra uke, senest",
      toHint: "Tom gir samme verdi for alle. Et høyere tall gir et spenn, og hver student får sin egen verdi.",
      refused: "Replay-scenariet ble ikke lagret. Se feltene over.",
      ownFixedDemand: (weeks: number) => `Fast serie på ${weeks} uker, siste verdi videre`,
      hiddenChange:
        "Uka for endringen trekkes for hver student og vises ikke for studentene. Antall uker vises ikke heller.",
      hiddenOwnNone:
        "Alle studenter får de samme verdiene. Antall uker og uka for endringen vises ikke for studentene.",
      hiddenOwnNoise:
        "Alle studenter får de samme verdiene, men sin egen etterspørsel rundt nivåene. Antall uker og uka for endringen vises ikke for studentene.",
      warnings: {
        easier: "Det gjør trolig Replay lettere.",
        inventory: (replay: string, classGame: string) =>
          `Advarsel: Startlager (${replay}) er høyere enn i Klassespillet (${classGame}).`,
        delay: (label: string, replay: string, classGame: string) =>
          `Advarsel: ${label} (${replay}) er kortere enn i Klassespillet (${classGame}).`,
        guided: (replay: string) =>
          `Advarsel: Veiledede uker (opptil ${replay}) gir hjelp som Standard-scenariet ikke gir.`,
        lower: (replay: string, classGame: string) =>
          `Advarsel: Høyeste nivå i etterspørselen (${replay}) er lavere enn i Klassespillet (${classGame}).`,
        lessVariable: (replay: string, classGame: string) =>
          `Advarsel: Spredningen (${replay}) er mindre enn i Klassespillet (${classGame}).`,
        noChange: "Advarsel: Etterspørselen skifter ikke nivå, slik den gjorde i Klassespillet.",
        // Story 10.9 (FR-83): a neighbour's view the Class games do not show.
        upstreamVisible:
          "Advarsel: Replay viser lager og restordre hos leddet oppstrøms, som Klassespillene ikke viser.",
        downstreamVisible:
          "Advarsel: Replay viser lager og restordre hos leddet nedstrøms, som Klassespillene ikke viser.",
        other: "Advarsel: Endringen kan gjøre Replay lettere.",
      },
      /** Story 10.9 (cut list, FEATURE_INFO_VISIBILITY, FR-83, UX-DR12): the Replay's own
       * Information visibility, shown only while the flag is on. [ASSUMPTION] draft copy. */
      infoVisibilityHelp:
        "Gjelder bare Replay, for alle studentene i Klasseøkta, også KI-spillerne. Starter som i Spillinnstillingene, og kan settes annerledes enn i Klassespillene. " +
        "Fabrikken har ingen nabo oppstrøms, og Detaljisten ingen nedstrøms.",
    },
    save: "Lagre Klasseøkt",
    saving: "Lagrer …",
    saveHint: "Du kan lagre uten å endre noe.",
    // [ASSUMPTION]
    saved: "Klasseøkten er lagret.",
    /** «Testspill» on the Klasseøkt (Story 6.20, FR-87): the Lecturer plays the stored settings
     * against three AI players before the Start date. [ASSUMPTION] draft copy, not in the spine. */
    testGame: {
      title: TEST_GAME,
      lead: "Spill mot tre KI-spillere med innstillingene slik de er lagret nå. Testspillet teller ikke i noen oversikt.",
      role: "Din rolle",
      start: "Start testspill",
      starting: "Starter testspill …",
      running: "Du har et testspill i gang.",
      resume: "Fortsett testspillet",
      previous: "Se forrige testspill",
      closed: "Testspill kan bare startes før Startdato.",
      refused: {
        session_locked: "Startdatoen er passert. Testspill kan bare startes før den.",
        test_game_running: "Du har allerede et testspill i gang her.",
        llm_unavailable: "LLM-spillerne kan ikke svare nå. Velg Regelbaserte spillere, eller be en Admin ordne det.",
        not_found: "Testspill er slått av.",
        unknown_role: "Spillinnstillingene har ikke denne rollen lenger. Velg en annen.",
      },
    },
    /** The locked Klasseøkt (Story 5.11, FR-18, GitHub issue 103). [ASSUMPTION] draft copy. */
    lock: {
      /** Under the title once the lock has frozen the session; `when` as «ti. 24. nov. kl. 10:00». */
      lockedAt: (when: string) =>
        `Låst ${when}. Spillinnstillinger, etterspørsel, KI-modus, Innsatsnivå, Debrief-modus, Replay-scenario, Obligatorisk og ventetid er frosset.`,
      /** The Start date has passed but the lock has not run yet (each minute) or was refused. */
      pending: "Startdatoen er passert. Spillinnstillinger, etterspørsel, KI-modus, Innsatsnivå, Debrief-modus, Replay-scenario, Obligatorisk og ventetid kan ikke endres.",
      // [ASSUMPTION] GitHub issue 109: the lock was refused, LLM players and no provider key.
      refused:
        "Klasseøkten kan ikke starte: KI-leverandøren for LLM-spillerne er ikke satt opp. Be en Admin ordne det. Låsen prøves igjen hvert minutt.",
      // [ASSUMPTION] Story 11.1 (issue #16): refused in production on a draft question set.
      refusedDraft:
        "Klasseøkten kan ikke starte: spørsmålene til den individuelle testen er et utkast som ikke er godkjent. En Admin må legge inn godkjente spørsmål. Låsen prøves igjen hvert minutt.",
      open: "Frister som ikke er passert, og Labtimer, kan fortsatt endres.",
      /** Story 12.1: while KI-vurdering can still change too. [ASSUMPTION] */
      openWithAssessment: "Frister som ikke er passert, Labtimer og KI-vurdering kan fortsatt endres.",
      labHoursOpen: "Labtimer kan fortsatt endres.",
      save: "Lagre frister",
      saveHint: "Bare frister som ikke er passert, blir lagret.",
      /** Story 12.1: «Lagre Klasseøkt» after the lock saves the deadlines and KI-vurdering. [ASSUMPTION] */
      saveHintWithAssessment: "Bare frister som ikke er passert, og KI-vurdering, blir lagret.",
      saved: "Fristene er lagret.",
    },
    // [ASSUMPTION] the save of LLM players refused (`llm_unavailable`).
    llmRefused: "LLM-spillere kan ikke velges ennå. Be en Admin velge en standardmodell.",
    // [ASSUMPTION] above the Klasseøkt an Assistant lecturer reads.
    assistantLead: "Du er Assistent i Klassen. Du ser Klasseøkten, men Faglærerne endrer den.",
    /** The Klasse page's list (Story 5.1). [ASSUMPTION] */
    list: {
      title: "Klasseøkter",
      empty: "Ingen Klasseøkter ennå.",
      create: "Lag Klasseøkt",
      creating: "Lager …",
      createFailed: "Klasseøkten ble ikke laget. Prøv igjen.",
      /** «Klasseøkt 2, opprettet 19. nov. 2026 kl. 10:00»: the running number keeps two sessions
       * created in the same minute apart (Issue #98). */
      item: (number: number, created: string) => `Klasseøkt ${number}, opprettet ${created}`,
      saved: "Lagret",
      unsaved: "Ikke lagret ennå",
      /** [ASSUMPTION] draft copy: a Class session made from an earlier one (Story 5.18, cut list,
       * FR-66). No IA row names the entry; it sits by «Lag Klasseøkt» on the Klasse page. */
      rerun: {
        open: "Lag fra en tidligere Klasseøkt",
        title: "Lag fra en tidligere Klasseøkt",
        source: "Klasseøkt å kopiere",
        group: (className: string, archived: boolean) => `${className}${archived ? " (arkivert)" : ""}`,
        option: (number: number, start: string) => `Klasseøkt ${number}, ${start}`,
        started: (date: string) => `start ${date}`,
        noStart: "uten startdato",
        keepSeed: "Etterspørsel uke for uke",
        keepSeedOn: "Den samme som i Klasseøkten du kopierer",
        keepSeedOff: "Ny, med samme mønster",
        keepSeedHelp: "Mønsteret kopieres alltid. Tallene uke for uke blir like bare om du velger den samme.",
        copied: "Spillinnstillinger, KI-modus, Innsatsnivå, Debrief-modus og Inaktivitetsgrense kopieres.",
        notCopied: "Datoer, Labtimer, Klasselisten, Fordeling og Obligatorisk kopieres ikke.",
        submit: "Lag kopi",
        submitting: "Lager kopi …",
        cancel: "Avbryt",
        none: "Du har ingen tidligere Klasseøkter.",
        loadFailed: "Klasseøktene kunne ikke hentes. Prøv igjen.",
        failed: "Kopien ble ikke laget. Prøv igjen.",
        refused: "Innstillingene i den gamle Klasseøkten godtas ikke lenger. Lag en ny Klasseøkt i stedet.",
      },
    },
    /** [ASSUMPTION] draft copy: what the Klasseøkt says of a copy until it is first saved (Story
     * 5.18, FR-66, FR-78). */
    copied: {
      from: (number: number, className: string) => `Kopiert fra Klasseøkt ${number} i ${className}.`,
      levelReplaced: (old: string, now: string) =>
        `Innsatsnivået ${old} finnes ikke for den nye modellen. Klasseøkten bruker standardnivået ${now}.`,
    },
    /** The four dates and the Datolinje (Story 5.2, FR-18, UX-DR51). «Datoer», «Startdato»,
     * «Spillfrist», «Debrieffrist» and «Testfrist» are EXPERIENCE.md's and mockup 03's own; the
     * rest is [ASSUMPTION] draft copy. */
    dates: {
      title: "Datoer",
      names: {
        start_at: "Startdato",
        play_deadline: "Spillfrist",
        debrief_deadline: "Debrieffrist",
        test_deadline: "Testfrist",
      },
      // [ASSUMPTION]
      none: "Ingen datoer ennå.",
      // [ASSUMPTION]
      timeZone: "Tidene er norsk tid.",
      // [ASSUMPTION] under the Testfrist while it is the prefilled value.
      testPrefilled: "Fylt ut 7 dager etter Debrieffristen. Du kan endre den.",
      // [ASSUMPTION] beside a date that has passed and no longer moves.
      passed: "Passert. Datoen kan ikke flyttes.",
      // [ASSUMPTION] Story 5.11: a date that can no longer change, as text: «ti. 24. nov. kl. 10:00».
      // A no-break space keeps «kl.» on the line of its time.
      dateText: (day: string, time: string) => `${day} kl. ${time}`,
      // [ASSUMPTION] a date not set, shown as text.
      notSet: "Ikke satt",
      // [ASSUMPTION] Story 5.11: the Startdato of a session locked before it (an early start).
      lockedStart: "Klasseøkten er låst. Startdatoen kan ikke flyttes.",
      /** A date on the Datolinje: «ti. 24. nov.». */
      day: (weekday: string, day: number, month: string) => `${weekday} ${day}. ${month}`,
      weekdays: ["sø.", "ma.", "ti.", "on.", "to.", "fr.", "lø."],
      /** The reason under a date the API refused. [ASSUMPTION] */
      errors: {
        order: (earlier: string) => `Må komme etter ${earlier}.`,
        before: (later: string) => `Må komme før ${later}.`,
        past: "Velg et tidspunkt fram i tid.",
        passed: "Datoen er passert og kan ikke flyttes.",
        required: "Klasseøkten har startet. Datoen kan ikke tas bort.",
        // [ASSUMPTION] GitHub issue 100: a field the browser holds half-typed; nothing is sent.
        incomplete: "Datoen og klokkeslettet er ikke fylt ut helt.",
      },
      // [ASSUMPTION] the alert line of a save refused for its dates.
      refused: "Datoene ble ikke lagret. Se feltene.",
      // [ASSUMPTION] a setting changed after the Start date (`session_locked`).
      locked: "Klasseøkten har startet. Innstillingene kan ikke endres lenger.",
      // [ASSUMPTION] FR-18: the warning that never blocks.
      playTimeShort: (weeks: number) =>
        `Det er kort tid mellom Startdato og Spillfrist for ${weeks} uker. Du kan likevel lagre.`,
    },
    /** Lab hours on the Datolinje (Story 5.6, FR-19, UX-DR51). «Labtime», «Legg til Labtime» and
     * the legend are EXPERIENCE.md's and mockup 03's own; the rest is [ASSUMPTION] draft copy. */
    labHours: {
      title: "Labtimer",
      add: "Legg til Labtime",
      /** «Blå firkant: Labtime, Datalab A2.»; `places` already joined. */
      legend: (places: string) => `Blå firkant: Labtime, ${places}.`,
      none: "Ingen Labtimer ennå.",
      /** A square in the Datolinje's text: «Labtime to. 26. nov. 14:15». */
      markLabel: "Labtime",
      /** One Lab hour: «to. 26. nov. 14:15–16:00, Datalab A2». */
      item: (day: string, start: string, end: string, place: string) => `${day} ${start}–${end}, ${place}`,
      ended: "ferdig",
      edit: "Endre",
      editLabel: (item: string) => `Endre Labtime ${item}`,
      addTitle: "Ny Labtime",
      editTitle: "Endre Labtime",
      date: "Dato",
      start: "Start",
      end: "Slutt",
      place: "Sted",
      placeHint: "For eksempel Datalab A2.",
      consequence: "Studentene får beskjed på e-post.",
      saveAdd: "Lagre Labtime",
      saveEdit: "Lagre endringen",
      remove: "Fjern Labtimen",
      cancel: "Avbryt",
      saving: "Lagrer …",
      removing: "Fjerner …",
      added: "Labtimen er lagt til.",
      changed: "Labtimen er endret.",
      removed: "Labtimen er fjernet.",
      errors: {
        dateMissing: "Velg en dato.",
        dateIncomplete: "Datoen er ikke fylt ut helt.",
        timeMissing: "Skriv et klokkeslett.",
        timeIncomplete: "Klokkeslettet er ikke fylt ut helt.",
        endNotAfterStart: "Slutt må være etter start.",
        tooLong: "En Labtime kan vare høyst 12 timer.",
        past: "Labtimen er allerede over. Velg et senere tidspunkt.",
        placeMissing: "Skriv hvor Labtimen er.",
        placeTooLong: "Skriv høyst 120 tegn.",
      },
      refused: "Labtimen ble ikke lagret. Se feltene.",
      hasEnded: "Labtimen er over og kan ikke endres lenger.",
    },
    /** The block «Fordeling» and its Fordelingsforhåndsvisning (Story 5.8, FR-20, UX-DR50). The
     * heading form, «Tomme seter får KI-spiller.», «Vis som liste», «Kjør fordeling på nytt» and
     * «Ikke bekreftet.» are EXPERIENCE.md's and mockup 03's own; the rest is [ASSUMPTION] draft copy. */
    allocation: {
      title: "Fordeling",
      notConfirmed: "Ikke bekreftet.",
      nobody: "Ingen registrerte studenter å fordele ennå.",
      open: "Se fordelingen",
      opening: "Henter fordelingen …",
      close: "Lukk",
      /** «Fordeling: 60 Klassespill à 4». */
      heading: (games: number) => `Fordeling: ${games} Klassespill à 4`,
      /** «240 studenter fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle.» */
      lead: (students: number) =>
        `${students} ${students === 1 ? "student" : "studenter"} fordeles tilfeldig. Hver søyle er ett spill, hver rad en Rolle.`,
      emptySeats: "Tomme seter får KI-spiller.",
      missing: (count: number) =>
        `${count} ${count === 1 ? "registrert student er" : "registrerte studenter er"} ikke med.`,
      missingRedraw: "Kjør fordeling på nytt for å ta dem med.",
      view: "Visning",
      chart: "Diagram",
      list: "Vis som liste",
      /** The chart's name, for its scroll region. */
      chartLabel: "Fordelingen, ett spill per søyle",
      /** «Spill 17». */
      game: (number: number) => `Spill ${number}`,
      /** One Seat in the game's line: «Ida, Detaljist». */
      seat: (name: string, role: string) => `${name}, ${role}`,
      aiPlayer: "KI-spiller",
      removed: "Ikke lenger i Klassen",
      redraw: "Kjør fordeling på nytt",
      redrawing: "Trekker …",
      redrawn: "Fordelingen er trukket på nytt.",
      noticeLine: "Ingen får beskjed før du bekrefter.",
      failed: "Fordelingen kunne ikke hentes. Prøv igjen.",
      locked: "Klasseøkten har startet. Fordelingen kan ikke trekkes på nytt.",
      // Story 5.9: «Bekreft fordeling» and «Fordelingen er bekreftet.» are EXPERIENCE.md's own; the
      // rest is [ASSUMPTION] draft copy.
      confirm: "Bekreft fordeling",
      confirming: "Bekrefter …",
      confirmed: "Fordelingen er bekreftet.",
      changed: "Fordelingen er endret siden du åpnet den. Se over den nye og bekreft igjen.",
      studentsRemoved:
        "En eller flere studenter er ikke lenger i Klassen. Plassene deres er nå tomme. Se over fordelingen og bekreft igjen.",
      confirmFailed: "Fordelingen ble ikke bekreftet. Prøv igjen.",
      confirmLocked: "Klasseøkten har startet. Fordelingen kan ikke bekreftes lenger.",
      redrawConfirmed: "Fordelingen er bekreftet og kan ikke trekkes på nytt.",
      // Issue 107 and Story 5.10: [ASSUMPTION] draft copy, except «Fordelingen er bekreftet».
      /** «Fordelingen er bekreftet ti. 24. nov. kl. 10:00.» in the open panel. */
      confirmedOn: (day: string, time: string) => `Fordelingen er bekreftet ${day} kl. ${time}.`,
      movedNotice: "De som flyttes eller byttes, får beskjed på e-post.",
      /** The selected game's Seats, where Students are moved and swapped: «Seter i Spill 3». */
      seatsHeading: (game: number) => `Seter i Spill ${game}`,
      /** «Flytt eller bytt Ida, Detaljist i Spill 3». */
      pick: (name: string, role: string, game: number) => `Flytt eller bytt ${name}, ${role} i Spill ${game}`,
      cancelPick: "Avbryt flyttingen",
      /** The buttons' visible text; each starts its full accessible name below. */
      pickShort: "Flytt eller bytt",
      swapShort: "Bytt",
      moveShort: "Flytt",
      /** Said once a Student is picked, and kept while another game is chosen. */
      picked: (name: string, role: string, game: number) =>
        `${name}, ${role} i Spill ${game}, skal flyttes. Velg et spill i diagrammet og så et sete.`,
      /** «Bytt Ida (Detaljist, Spill 3) med Sara (Grossist, Spill 5)». */
      swapWith: (name: string, role: string, game: number, other: string, otherRole: string, otherGame: number) =>
        `Bytt ${name} (${role}, Spill ${game}) med ${other} (${otherRole}, Spill ${otherGame})`,
      /** «Flytt Ida (Detaljist, Spill 3) til ledig sete: Grossist i Spill 5». */
      moveTo: (name: string, role: string, game: number, toRole: string, toGame: number) =>
        `Flytt ${name} (${role}, Spill ${game}) til ledig sete: ${toRole} i Spill ${toGame}`,
      /** «Ida er flyttet til Grossist i Spill 5.» */
      moved: (name: string, role: string, game: number) => `${name} er flyttet til ${role} i Spill ${game}.`,
      swapped: (name: string, other: string) => `${name} og ${other} har byttet plass.`,
      moving: "Flytter …",
      moveFailed: "Flyttingen ble ikke lagret. Prøv igjen.",
      moveLocked: "Klasseøkten har startet. Ingen kan flyttes lenger.",
      moveLastStudent: "Spillet ville stått uten studenter. Bytt med en student i stedet.",
      moveInvalid: "Det setet kan ikke brukes. Velg et annet.",
      moveStarted: "Spillet har startet. Ingen kan flyttes inn eller ut av det.",
      // Story 5.12: [ASSUMPTION] draft copy. The Class games are open on the frozen settings.
      opened: "Klassespillene er klare. Ingen av spillene har startet ennå.",
      /** «6 studenter i 2 Klassespill. Hver søyle er ett spill, hver rad en Rolle.» */
      openedLead: (students: number, games: number) =>
        `${students} ${students === 1 ? "student" : "studenter"} i ${games} Klassespill. Hver søyle er ett spill, hver rad en Rolle.`,
      openedSeats: "Tomme seter er fylt med KI-spillere.",
      // Story 5.13: [ASSUMPTION] draft copy. After the lock, Students no Class game could seat.
      /** «2 registrerte studenter har ikke sete: Ida Hansen, Sara Berg.» */
      withoutSeat: (names: readonly string[]) =>
        `${names.length} ${names.length === 1 ? "registrert student har" : "registrerte studenter har"} ikke sete: ${names.join(", ")}.`,
      /** A Class game's state, shown apart after its Seats. */
      lifecycle: {
        not_started: "Ikke startet.",
        running: "I gang.",
        playing_out: "Spilles ferdig.",
        finished: "Ferdig.",
      },
      // Story 5.17 (cut list, FEATURE_STUDENT_CHOICE): [ASSUMPTION] draft copy. The allocation
      // method as Valgknapper, saved with «Lagre Klasseøkt», and the block once Students choose.
      method: "Fordelingsmåte",
      methodRandom: "Tilfeldig",
      methodChoice: "Studentene velger",
      methodRandomHelp: "Du trekker og bekrefter fordelingen her.",
      methodChoiceHelp:
        "Studentene velger spill og sete selv før startdatoen. Den som ikke har valgt da, får et sete ved trekning. Fordelingsmåten kan ikke endres etter at den er lagret.",
      methodChoicePending: "Lagre Klasseøkt for å åpne valget. Studentene får beskjed på e-post.",
      methodConfirmed: "Fordelingen er bekreftet. Fordelingsmåten kan ikke endres lenger.",
      choiceState: "Studentene velger spill og sete selv.",
      // GitHub issue 115: what fills the empty Seats at the lock while Students choose.
      choiceEmptySeats: "På startdatoen trekkes studenter som ikke har valgt, inn i ledige seter først. Seter som da er tomme, får KI-spiller.",
      /** «3 studenter har valgt sete. Hver søyle er ett spill, hver rad en Rolle.» */
      choiceLead: (students: number) =>
        `${students} ${students === 1 ? "student har" : "studenter har"} valgt sete. Hver søyle er ett spill, hver rad en Rolle.`,
      /** «2 registrerte studenter har ikke valgt ennå. De får et sete ved trekning på startdatoen.» */
      choiceMissing: (count: number) =>
        `${count} ${count === 1 ? "registrert student har" : "registrerte studenter har"} ikke valgt ennå. De får et sete ved trekning på startdatoen.`,
      freeSeat: "Ledig",
    },
    /** «Velg spill og sete» (Story 5.17, UX-DR62). «Grossist, ledig», «Ta setet Grossist i Spill
     * 17», «Setet ble tatt av en annen. Velg et annet.» and «Du fikk et sete ved trekning:
     * Grossist i Spill 17.» are the epic's own; the rest is [ASSUMPTION] draft copy. */
    seatChoice: {
      title: "Velg spill og sete",
      /** «class-of-1994, Klasseøkt 1». */
      session: (className: string, number: number) => `${className}, Klasseøkt ${number}`,
      /** «Velg før startdatoen ti. 24. nov. kl. 10:00. Du kan bytte til et annet ledig sete fram til da.» */
      before: (day: string, time: string) =>
        `Velg før startdatoen ${day} kl. ${time}. Du kan bytte til et annet ledig sete fram til da.`,
      beforeNoDate: "Velg før startdatoen. Du kan bytte til et annet ledig sete fram til da.",
      /** «Ditt sete: Grossist i Spill 17.» */
      mine: (role: string, game: number) => `Ditt sete: ${role} i Spill ${game}.`,
      none: "Du har ikke valgt sete ennå.",
      /** «Spill 17». */
      game: (number: number) => `Spill ${number}`,
      /** How many of a game's Seats are free: «2 ledige», «1 ledig», «Fullt». */
      freeCount: (count: number) => (count === 0 ? "Fullt" : `${count} ${count === 1 ? "ledig" : "ledige"}`),
      /** «Grossist, ledig». */
      free: (role: string) => `${role}, ledig`,
      /** «Grossist, Ida Hansen». */
      held: (role: string, name: string) => `${role}, ${name}`,
      /** «Grossist, ditt sete». */
      own: (role: string) => `${role}, ditt sete`,
      /** The visible mark on a free Seat's button; its name is «Grossist, ledig». */
      pick: "Velg",
      /** Under «Ta setet …» for a Student who holds a Seat: «Du gir fra deg Grossist i Spill 1.» */
      leaves: (role: string, game: number) => `Du gir fra deg ${role} i Spill ${game}.`,
      removed: "Ikke lenger i Klassen",
      aiPlayer: "KI-spiller",
      /** «Ta setet Grossist i Spill 17». */
      take: (role: string, game: number) => `Ta setet ${role} i Spill ${game}`,
      taking: "Tar setet …",
      conflict: "Setet ble tatt av en annen. Velg et annet.",
      failed: "Setet ble ikke tatt. Prøv igjen.",
      invalid: "Det setet finnes ikke lenger. Velg et annet.",
      closed: "Klasseøkten har startet. Setet kan ikke byttes lenger.",
      /** «Du fikk et sete ved trekning: Grossist i Spill 17.» */
      drawn: (role: string, game: number) => `Du fikk et sete ved trekning: ${role} i Spill ${game}.`,
      /** The Lenke on Hjem while the choice is open. */
      open: "Velg spill og sete",
      openLine: "Du velger spill og sete selv før startdatoen.",
    },
    /** The Lærerhjem's «Venter» and «Neste frist» (Stories 5.2, 5.9, UX-DR56). [ASSUMPTION] */
    home: {
      /** «class-of-1994: Klasseøkt 2 mangler datoer og bekreftet fordeling». */
      lacks: (className: string, number: number, what: readonly ("dates" | "allocation")[]) =>
        `${className}: Klasseøkt ${number} mangler ${what.map((item) => LACKS[item]).join(" og ")}`,
      nextDate: (dateName: string, number: number, className: string) =>
        `${dateName}, Klasseøkt ${number}, ${className}`,
    },
  },

  /** The Student's Class game (Epic 6). Shown before the Debrief: `npm run check:copy` holds it to
   * the pre-Debrief rules. */
  games: {
    /** «Regler før første ordre» (Story 6.2, FR-84, FR-14, UX-DR63, UX-DR70). The title is the
     * spine's; everything else is [ASSUMPTION] draft copy for the founder's review. It states the
     * game's own delays, Veiledede uker and rates, never the number of Weeks, and recommends no
     * Order. */
    briefing: {
      title: "Regler før første ordre",
      lead: (role: string, number: number | null) =>
        `Du er ${role} i ${gameName(number)}. Kjeden har fire roller: Fabrikk, Distributør, Grossist og Detaljist. Hver uke sender du enheter til den som bestiller fra deg, og legger inn én egen ordre.`,
      goal: {
        title: "Målet",
        text: "Dere skal få lavest mulig totalkostnad for hele kjeden, ikke bare for ditt eget sete.",
        rates: (holding: string, backorder: string) =>
          `Hver enhet på lager koster ${holding} kr per uke. Hver enhet i restordre koster ${backorder} kr per uke.`,
      },
      week: {
        title: "Slik går en uke",
        same: "Alle setene legger inn ordre for den samme uka. Når alle har lagt inn sin ordre, regnes uka, og neste uke åpner.",
        ship: "Det du har på lager, må du sende, opp til det som er bestilt fra deg. Du kan ikke holde enheter tilbake.",
        backlog: "Det du ikke kan sende, blir restordre. Restordre sendes så snart du har enheter.",
      },
      /** [ASSUMPTION] Story 6.22 (cut list, FEATURE_CAPACITY, FR-12): draft copy for the founder's
       * review. Shown only when the game's snapshot caps a Role. Never a number of Weeks. */
      capacity: {
        title: "Kapasitet",
        /** «Grossisten kan sende høyst 6 enheter per uke.» */
        role: (role: string, units: number) => `${role} kan sende høyst ${unitsText(units)} per uke.`,
        every: (units: number) => `Hver rolle kan sende høyst ${unitsText(units)} per uke.`,
        both: "En rolle med kapasitet kan ha lager og restordre samtidig: enhetene ligger på lager mens ordrene venter.",
        mine: "Rollen din har kapasitet. Tabellen i spillet viser derfor Lager og Restordre hver for seg, over Netto lager.",
        /** The Role, definite: «Grossisten». */
        definite: { retailer: "Detaljisten", wholesaler: "Grossisten", distributor: "Distributøren", factory: "Fabrikken" },
      },
      delays: {
        title: "Forsinkelsene",
        /** Every Role but Fabrikk: the order reaches the supplier, then the goods travel back. */
        order: (weeks: string, supplier: string) => `Ordren din kommer fram til ${supplier} ${weeks} etter at du la den inn.`,
        shipping: (weeks: string) => `Det som sendes til deg, er ${weeks} på vei før det kommer fram.`,
        /** Fabrikk orders from its own production. */
        production: (orderWeeks: string, productionWeeks: string) =>
          `Ordren din går til produksjon ${orderWeeks} etter at du la den inn. Produksjonen tar ${productionWeeks}.`,
        /** No sum of the delays: the web app works out no game quantity (AD-1). */
        earliest:
          "Det du bestiller nå, kommer altså tidligst fram etter begge forsinkelsene, og senere hvis leverandøren mangler enheter.",
        earliestFactory: "Det du bestiller nå, kommer altså tidligst fram etter begge forsinkelsene.",
        onTheWay: "Enheter du har bestilt og ennå ikke fått, står som På vei.",
        /** The supplier, definite: «Distributøren». */
        supplier: { wholesaler: "Grossisten", distributor: "Distributøren", factory: "Fabrikken" },
        weeks: (count: number) => (count === 1 ? "én uke" : `${countWord(count)} uker`),
      },
      guided: {
        title: "Veiledede uker",
        some: (count: number) =>
          `${count === 1 ? "Den første uka er en veiledet uke." : `De første ${countWord(count)} ukene er veiledede uker.`} Ordren er fast og legges inn for deg, så du kan bli kjent med tallene. Uka går videre når alle har åpnet den.`,
        none: "Dette spillet har ingen veiledede uker. Du legger inn din egen ordre fra første uke.",
      },
      together: {
        title: "Slik spiller dere",
        continues: "Spill som om virksomheten fortsetter.",
        arrange: "Dere kan avtale når dere spiller, men dere skal ikke snakke om ordrer eller tall med de andre i kjeden.",
      },
      example: {
        title: "Én uke forklart",
        // [ASSUMPTION] Epic 6: the graph strip over the worked Uke (`09-alle-sider.png`).
        strip: "Slik viser spillet ukene: grafen over tabellen, én kolonne per uke, og nå-streken ved uka du spiller. Her Uke 4 for en Grossist.",
        caption: "Uke 11 for en Grossist",
        term: "Rad",
        value: "Tall",
        meaning: "Hva det betyr",
        /** The worked Uke's rows, top to bottom (Demodata, Design Notes of Story 6.2), each with the
         * numbers of `EXAMPLE` in `modules/games/briefing.ts`. */
        rows: {
          incomingOrder: (w: WorkedWeekCopy) =>
            `Det Detaljisten bestilte. Med ${w.backlogBefore} i restordre fra før må Grossisten sende ${w.owed}.`,
          incomingDelivery: (w: WorkedWeekCopy) =>
            `Enheter som kom fram denne uka. Med ${w.inventoryBefore} på lager fra før har Grossisten ${w.onHand}.`,
          unitsShipped: () => "Grossisten sender alt den har, opp til det den skal sende.",
          inventory: (w: WorkedWeekCopy) => `Det som er igjen etter sendingen: ${w.onHand} − ${w.shipped}.`,
          backlog: (w: WorkedWeekCopy) =>
            `Det Grossisten ikke kunne sende: ${w.owed} − ${w.shipped}. Det sendes så snart enhetene finnes.`,
          netInventory: (w: WorkedWeekCopy) =>
            `Lager minus restordre: ${w.inventoryAfter} − ${w.backlogAfter}. Under null betyr restordre. Spillets tabell viser denne raden.`,
          supplyLine: () => "Enheter Grossisten har bestilt og ennå ikke fått.",
        },
        /** «Denne uka: 13 enheter i restordre, hver til 1,00 kr. Lager 0 gir ingen lagerkostnad.» No
         * product: the web app computes no cost (AD-1). */
        cost: (backlog: number, inventory: number, rate: string) =>
          `Denne uka: ${backlog} enheter i restordre, hver til ${rate} kr. Lager ${inventory} gir ingen lagerkostnad.`,
        demoData: "Demodata",
      },
      /** Opens the Startoppgave (Story 6.3). */
      done: "Jeg har lest reglene",
    },
    /** The Startoppgave (Story 6.3, FR-85, UX-DR63, UX-DR70). The title, the error, the right and
     * wrong lines, the final question with its four answers and the done line are the spine's
     * (epics, EXPERIENCE.md → States); the rest is [ASSUMPTION] draft copy for the founder's
     * review. The items' own prompts are content (`modules/content`), not copy. It never names
     * the game. */
    startingTask: {
      // A soft hyphen: where the heading must break (200 % text), it breaks as «Start-oppgave».
      title: "Start­oppgave",
      lead: "Noen korte regnestykker med tallene fra én kolonne i ukestabellen. Oppgaven teller ikke, og du går videre uansett hva du svarer.",
      demoData: "Demodata",
      progress: (n: number, of: number) => `Oppgave ${n} av ${of}`,
      notWhole: "Skriv et helt tall.",
      send: "Send svar",
      /** «Riktig. Svaret er 3: 0 − 13 + 16.» The sum is the api's terms, written out. */
      right: (expected: string, sum: string) => `Riktig. Svaret er ${expected}: ${sum}.`,
      wrong: (expected: string, sum: string) => `Ikke riktig. Svaret er ${expected}: ${sum}.`,
      final: {
        question: "Har du spilt et spill som ligner dette før?",
        optional: "Svaret er frivillig.",
        choices: { yes: "Ja", no: "Nei", unknown: "Vet ikke" },
        skip: "Hopp over",
        none: "Velg et svar, eller hopp over.",
      },
      done: "Ferdig. Gå til Uke 1.",
      toHome: "Til Hjem",
    },
    /** Starting the Class game (Story 6.5, FR-22, UX-DR78). «Start spillet», its consequence line
     * and «Gå til Uke 1» are the spine's (EXPERIENCE.md → Start); the rest is [ASSUMPTION] draft
     * copy for the founder's review. */
    start: {
      start: "Start spillet",
      consequence: "Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.",
      /** «Gå til Uke 11». */
      toWeek: (week: number) => `Gå til Uke ${week}`,
      notReady: NOT_READY,
      failed: "Spillet ble ikke startet. Prøv igjen.",
      errors: {
        starting_task_required: "Gjør Startoppgaven først.",
        game_not_ready: NOT_READY,
      },
    },
    /** The scheduling aid (Story 6.19, FR-22): a date and a time to play, never text. «Foreslå
     * tidspunkt» and the range error are the epic's; the rest is [ASSUMPTION] draft copy for the
     * founder's review (EXPERIENCE.md leaves the surface undrawn). */
    timeProposal: {
      open: "Foreslå tidspunkt",
      title: "Foreslå tidspunkt",
      date: "Dato",
      time: "Klokkeslett",
      consequence: "De andre i spillet får beskjed og kan godta tidspunktet.",
      replaces: "Forslaget erstatter det som står nå.",
      send: "Send forslaget til gruppen",
      sending: "Sender …",
      cancel: "Avbryt",
      sent: "Forslaget er sendt.",
      /** «Kari Nordmann foreslår å spille to. 26. nov. kl. 14:15.» */
      proposed: (name: string, when: string) => `${name} foreslår å spille ${when}.`,
      proposedMine: (when: string) => `Du foreslår å spille ${when}.`,
      someone: "En Student",
      /** «Godtatt av Per Hansen og deg.» */
      acceptedBy: (names: string) => `Godtatt av ${names}.`,
      you: "deg",
      noneAccepted: "Ingen har godtatt ennå.",
      accept: "Godta tidspunktet",
      accepting: "Godtar …",
      failed: "Det gikk ikke. Prøv igjen.",
      errors: {
        dateMissing: "Velg en dato.",
        timeMissing: "Velg et klokkeslett.",
        /** The epic's: «Velg et tidspunkt mellom nå og Spillfristen, ti. 8. des. kl. 14:00.» */
        range: (deadline: string) => `Velg et tidspunkt mellom nå og Spillfristen, ${deadline}.`,
      },
      refusals: {
        game_finished: "Spillet er ferdig.",
        proposal_gone: "Forslaget er byttet ut eller har gått ut.",
        own_proposal: "Du foreslo selv dette tidspunktet.",
      },
    },
    /** The play route (Story 6.5): the Topplinje's «Uke 11» over «Grossist, Spill 17» (DESIGN.md
     * → Topplinje), and the four Seats. A finished game shows «Spillet er ferdig» (Story 6.18). */
    play: {
      week: (week: number) => `Uke ${week}`,
      roleGame: (role: string, number: number | null) => `${role}, ${gameName(number)}`,
      /** Story 10.4: «Grossist, Replay» under the Uke in the Replay's Topplinje. [ASSUMPTION] */
      roleReplay: (role: string) => `${role}, Replay`,
      /** Story 13.4: «Grossist, Oppfølgingsspill» in the Oppfølgingsspill's Topplinje. [ASSUMPTION] */
      roleMakeup: (role: string) => `${role}, Oppfølgingsspill`,
      /** Story 6.20: a test Game leads back to where it was started. [ASSUMPTION] */
      toClassSession: "Tilbake til Klasseøkta",
      /** «Spillet er ferdig» (Story 6.18, FR-28, UX-DR30, EXPERIENCE.md → Spillet er ferdig): the
       * spine's strings in the spine's order. `failed` is the page-error line. */
      end: {
        title: "Spillet er ferdig",
        totalLabel: "Kjedens totalkostnad",
        totalNote: "Fire Roller, to kostnadsarter, hele spillet.",
        why: "Hvorfor ble den slik? Det finner dere ut i Debriefen, med alle fire Rollene.",
        toDebrief: "Gå til Debrief",
        /** Story 8.14 (FR-38, EXPERIENCE.md → Spill → Ended by playout) [ASSUMPTION] draft copy:
         * the game ended at the Spillfrist. No blame, and never how many Uker the KI-spillere
         * played. */
        playedOut: "Spillet ble avsluttet ved Spillfristen. KI-spillere spilte det ferdig.",
        /** Story 9.2: the Faglærer holds the Debriefs until all Class games have finished; never
         * how many remain. [ASSUMPTION] */
        held: "Debriefen åpner når alle Klassespillene er ferdige.",
      },
      /** «Replay er ferdig» (Story 10.5, FR-50, UX-DR64, EXPERIENCE.md → Replay, Finished): the
       * spine's title, «Totalkostnad» and button; the note under the total is [ASSUMPTION]. */
      replayEnd: {
        title: "Replay er ferdig",
        totalLabel: "Totalkostnad",
        totalNote: (role: string) => `${role}, to kostnadsarter, hele Replay.`,
        toWalkthrough: "Gå til gjennomgangen",
      },
      /** A Replay closed at the Testfrist without its last Uke (Story 10.6, FR-18, EXPERIENCE.md →
       * Replay): not finished, no Totalkostnad, no walkthrough. [ASSUMPTION] */
      replayClosed: {
        title: "Replay stengt",
        lead: "Testfristen er ute. Replay ble stengt før siste uke og er ikke fullført.",
        kept: "Ordrene du la inn, er lagret som de var.",
      },
      /** Story 13.4: an Oppfølgingsspill closed at the Testfrist without its last Uke, as the
       * Replay's. [ASSUMPTION] */
      makeupClosed: {
        title: "Oppfølgingsspill stengt",
        lead: "Testfristen er ute. Oppfølgingsspillet ble stengt før siste uke og er ikke fullført.",
      },
      /** Ordrefelt (Story 6.10, DESIGN.md → Ordrefelt, UX-DR20). The label is the spine's; the
       * Veiledet uke line is [ASSUMPTION] draft copy. It never says how many Veiledede uker are
       * left (FR-14): the briefing told that. */
      order: {
        label: (week: number) => `Din ordre for Uke ${week}`,
        guided: "Veiledet uke. Ordren er fast og legges inn automatisk.",
        /** The editable states (Story 6.11, EXPERIENCE.md → Ordrefelt). Every string is the
         * spine's except `stepped`, which is [ASSUMPTION] draft copy. */
        placeholder: "Antall enheter",
        help: (max: string) => `Hele tall fra 0 til ${max}.`,
        last: (order: string) => `Sist Uke bestilte du ${order}.`,
        invalid: (max: string) => `Skriv et helt tall fra 0 til ${max}.`,
        tooLarge: (value: string, max: string) => `${value} er mer enn ${max}. Skriv et helt tall fra 0 til ${max}.`,
        fewer: "Én færre",
        more: "Én flere",
        /** Announced politely after − or +: «24 enheter». [ASSUMPTION] */
        stepped: (value: string) => `${value} enheter`,
        confirm: "Bekreft ordre",
        confirmOn: (value: string) => `Bekreft ordre på ${value}`,
        arrives: (week: number) => `Kommer fram om lag Uke ${week}. Kan ikke endres etter at du har bekreftet.`,
        /** Submitting and Confirmed (Story 6.12, EXPERIENCE.md → State Patterns → Spill). `next`
         * is [ASSUMPTION] draft copy of 2026-11-14 (open-assumptions.md). */
        sending: (value: string) => `Sender ordre på ${value} …`,
        sent: (value: string) => `Ordren på ${value} er sendt.`,
        /** Confirmed while the game waits for others (Story 6.14): «Ordren på 24 er sendt. Venter
         * på Jonas (3 min).» */
        sentWaiting: (value: string, who: string) => `Ordren på ${value} er sendt. Venter på ${who}.`,
        next: "Skjermen går videre når alle har bestilt. Du får e-post hvis spillet venter på deg.",
        /** A send that failed, timed out or found the device offline (Story 6.13, EXPERIENCE.md →
         * State Patterns → Spill, UX-DR60). The spine's strings, except `weekGone` and `seatGone`,
         * which are [ASSUMPTION] draft copy for `409 week_not_open` and `409 seat_not_yours`. A
         * non-breaking space keeps «…» on the line of the word before it (GitHub issue 130). */
        failed: "Ordren ble ikke sendt. Ingenting er bestilt ennå.",
        retry: (value: string) => `Prøv å sende ${value} igjen`,
        checking: "Vi vet ikke om ordren kom fram. Sjekker …",
        offline: (value: string) => `Ordren på ${value} er ikke sendt.`,
        reconnected: "Tilkoblet igjen. Ordren er ikke sendt ennå.",
        weekGone: (week: number, value: string) => `Uke ${week} er over. Ordren på ${value} ble ikke sendt.`,
        seatGone: (value: string) => `Du har ikke dette setet lenger. Ordren på ${value} ble ikke sendt.`,
        /** Story 10.6: `409 test_deadline_passed`, a Replay past the Testfrist. [ASSUMPTION] */
        deadlineGone: (value: string) => `Testfristen er ute. Ordren på ${value} ble ikke sendt.`,
      },
      /** The Uke-overgang (Story 6.15, EXPERIENCE.md → Uke-overgang, UX-DR23): «Uke 11 er ferdig
       * regnet», «Restordre 13 blir 20», «Denne uka: 20 restordre × 1,00 = 20,00 kr» and «Hopp
       * over» are the spine's; the Lager part of the cost line and `draftDropped` are [ASSUMPTION]
       * draft copy. */
      summary: {
        done: (week: number) => `Uke ${week} er ferdig regnet`,
        skip: "Hopp over",
        change: (from: string, to: string) => `${from} blir ${to}`,
        backorderPart: (units: string, rate: string) => `${units} restordre × ${rate}`,
        /** [ASSUMPTION] */
        holdingPart: (units: string, rate: string) => `${units} lager × ${rate}`,
        weekCost: (parts: string[], sum: string) =>
          parts.length === 0 ? `Denne uka: ${sum}` : `Denne uka: ${parts.join(" + ")} = ${sum}`,
        /** Opens «Alle rader og kostnad» at «Kostnad så langt» on phone (Story 6.16). */
        costLink: "Kostnad så langt",
        /** A typed Order that was never sent when its Uke closed. [ASSUMPTION] */
        draftDropped: (week: number, value: string) => `Uke ${week} er over. Du skrev ${value}, men ordren ble ikke sendt.`,
      },
      /** The Topplinje's Totalkostnad pair as one button on phone (Story 6.16, EXPERIENCE.md →
       * Topplinje): «Totalkostnad 68,00 kr, vis alle rader og kostnad». */
      totalCostButton: (amount: string) => `Totalkostnad ${amount}, vis alle rader og kostnad`,
      /** «Alle rader og kostnad» (Story 6.16, DESIGN.md → Alle rader og kostnad, `05-spill.png`
       * middle). The link, title, «Lukk» and the column lines are the spine's; `sumRowNote` is
       * [ASSUMPTION] draft copy. */
      allRows: {
        link: "Alle rader og kostnad",
        title: (week: number) => `Alle rader, Uke ${week}`,
        close: "Lukk",
        netLine: (week: number) => `Netto lager i kolonne ${week}`,
        positionLine: (week: number) => `Posisjon i kolonne ${week}`,
        /** Read where «Totalkostnad over tid» stands, which is hidden from screen readers. [ASSUMPTION] */
        sumRowNote: "Totalkostnad over tid står som tall i raden Sum, kr i tabellen over.",
      },
      /** «Kostnad så langt» (`cost-panel`, Story 6.16, DESIGN.md, EXPERIENCE.md → Kostnad så langt).
       * The labels and «Vis som tabell» are the spine's; «Vis som graf», the table caption and the
       * chart's `<title>` are [ASSUMPTION] draft copy. */
      costPanel: {
        title: "Kostnad så langt",
        holding: "Lagerkostnad",
        backorder: "Restordrekostnad",
        total: "Totalkostnad",
        overTime: "Totalkostnad over tid",
        showTable: "Vis som tabell",
        /** [ASSUMPTION] */
        showChart: "Vis som graf",
        /** The table's columns: Uke / Lager / Restordre / «Sum, kr», each a running sum in kroner. */
        holdingColumn: "Lager",
        backorderColumn: "Restordre",
        sumColumn: "Sum, kr",
        /** [ASSUMPTION] */
        tableCaption: "Totalkostnad over tid, i kroner",
        /** [ASSUMPTION] */
        chartSvg: "Graf over Totalkostnad over tid, lagerkostnad nederst og restordrekostnad øverst.",
        week: (week: number) => `Uke ${week}`,
      },
      /** Kjedens regning and Kjedens kostnad over tid (Story 6.18, DESIGN.md `chain-bill`,
       * `chain-cost-chart`, UX-DR30): shared with the Debrief (Epic 9). The headings, columns,
       * «Kjeden», «(deg)» and «Vis som tabell» are the spine's; captions and SVG titles are
       * [ASSUMPTION] draft copy. */
      chain: {
        bill: "Kjedens regning",
        role: "Rolle",
        holding: "Lager",
        backorder: "Restordre",
        sum: "Sum",
        chain: "Kjeden",
        /** «Grossist (deg)». */
        own: (role: string) => `${role} (deg)`,
        /** [ASSUMPTION] */
        billCaption: "Kjedens regning per Rolle, i kroner: lagerkostnad, restordrekostnad og sum.",
        overTime: "Kjedens kostnad over tid",
        showTable: "Vis som tabell",
        /** [ASSUMPTION] */
        showChart: "Vis som graf",
        /** [ASSUMPTION] */
        tableCaption: "Kjedens kostnad over tid, i kroner",
        /** [ASSUMPTION] */
        chartSvg: "Graf over kjedens kostnad over tid, lagerkostnad nederst og restordrekostnad øverst.",
        week: (week: number) => `Uke ${week}`,
      },
      /** The week table (Story 6.6, DESIGN.md → Graf over tabell, UX-DR17, UX-DR18). The region
       * name, «Sveip for tidligere uker», «Din ordre» and «Kost, kr» are the spine's; the label for
       * known arrivals is [ASSUMPTION] draft copy (EXPERIENCE.md gives no string). */
      table: {
        region: "Graf og tabell",
        swipe: "Sveip for tidligere uker",
        order: "Din ordre",
        cost: "Kost, kr",
        /** The running Totalkostnad per Uke, in Alle rader (Story 6.16, DESIGN.md). */
        sum: "Sum, kr",
        /** Read with a known arrival's cell: «4, bestilt, ikke garantert». [ASSUMPTION] */
        arrival: "bestilt, ikke garantert",
        /** Read in the empty Din ordre cell at nå. [ASSUMPTION] */
        noOrderYet: "ingen ordre ennå",
        /** Read with the typed Order's two cells, Din ordre at nå and its arrival in Levering:
         * «24, din ordre, ikke bekreftet» (Story 6.11). [ASSUMPTION] */
        typed: "din ordre, ikke bekreftet",
        /** Read with the same two cells once the Order is sent: «24, din ordre» (Story 6.12).
         * [ASSUMPTION] */
        confirmed: "din ordre",
        /** The visible key under the table. [ASSUMPTION] */
        arrivalKey: "Tall i ramme: bestilt, ikke garantert.",
      },
      /** The graph over the table (Story 6.7, DESIGN.md → Graf over tabell, UX-DR16). «Nå»,
       * «Kost per uke», the key «restordre 1,00 / lager 0,50» and the direct labels («Restordre
       * 13», «Posisjon 3») are the spine's; the rest is [ASSUMPTION] draft copy. */
      graph: {
        /** The Netto lager field's title, as drawn in `05-spill.png`. [ASSUMPTION] */
        netTitle: "Lager over null, restordre under",
        costTitle: "Kost per uke",
        /** The key's two parts, each after its colour square: «restordre 1,00 / lager 0,50». */
        backorderKey: (rate: string) => `restordre ${rate}`,
        holdingKey: (rate: string) => `lager ${rate}`,
        /** Shown by the key in the Uke the Kost per uke axis grows. [ASSUMPTION] (DESIGN.md) */
        axisGrown: (top: string) => `Aksen går nå til ${top} kr.`,
        costTick: (top: string) => `${top} kr`,
        now: "Nå",
        /** Direct labels at the now-point, by the sign of Netto lager («Restordre 13», «Lager 12»,
         * «Netto lager 0»). The 0 and Lager forms are [ASSUMPTION]. */
        netLabel: (net: number, text: string) =>
          net < 0 ? `Restordre ${text}` : net > 0 ? `Lager ${text}` : `Netto lager ${text}`,
        positionLabel: (text: string) => `Posisjon ${text}`,
        /** The charts' `<title>`s, the alternative text a PDF reader gets (AD-18). [ASSUMPTION] */
        netSvg: "Graf over Netto lager og Posisjon per uke. Tallene står i tabellen under.",
        netAxisSvg: "Akse for Netto lager og Posisjon, i enheter.",
        /** The Spillkort's mini graph (Story 6.17). [ASSUMPTION] */
        netMiniSvg: "Graf over Netto lager per uke. Tallene står i tabellen under.",
        netMiniAxisSvg: "Akse for Netto lager, i enheter.",
        costSvg: "Graf over Kost per uke, lagerkostnad nederst og restordrekostnad øverst. Tallene står i raden Kost, kr.",
        costAxisSvg: "Akse for Kost per uke, i kroner.",
        /** Story 10.4 (UX-DR19, EXPERIENCE.md → Hidden information): the projection's sentence,
         * the dashed line's text alternative, under the table in the Replay only. The form with an
         * Order is the spine's; the one with nothing typed is [ASSUMPTION] draft copy. Numbers come
         * formatted («−5»); `weeks` is the delay horizon. */
        projection: (weeks: number, position: string, order: string | null, horizon: string, incoming: string, value: string) =>
          order === null
            ? `Den stiplede linja viser netto lager om ${weeksInWords(weeks)}: ${formula(`${position} − ${horizon} × ${incoming} = ${value}`)} hvis du ikke bestiller og ordre inn holder seg. Ikke garantert.`
            : `Den stiplede linja viser netto lager om ${weeksInWords(weeks)}: ${formula(`${position} + ${order} − ${horizon} × ${incoming} = ${value}`)} hvis ordre inn holder seg. Ikke garantert.`,
      },
      /** Kjedebånd (Story 6.9, DESIGN.md → Kjedebånd, UX-DR14, UX-DR73). The labels («Ordre inn
       * 8», «Din ordre», «Levering 4», «Sendt 4», «Lager 12», «Restordre 13», «På vei 16») and the
       * end labels «Produksjon» and «Kundene» are the spine's; the rest is [ASSUMPTION] draft copy. */
      band: {
        production: "Produksjon",
        customers: "Kundene",
        order: "Din ordre",
        /** The Order of the KI-spiller that took the own Seat over (Story 8.4): «KI-ordre 9», never
         * «Din ordre». [ASSUMPTION] */
        aiOrder: "KI-ordre",
        labelled: (term: string, value: string) => `${term} ${value}`,
        /** With a typed Order (Story 6.11, UX-DR14): «På vei 16 + 24» drawn, «På vei 16 pluss 24»
         * read. */
        withTyped: (label: string, typed: string) => `${label} + ${typed}`,
        withTypedRead: (label: string, typed: string) => `${label} pluss ${typed}`,
        /** Read after «På vei 16» when units are overdue: «På vei 16, av dem 7 uten kjent uke».
         * [ASSUMPTION] */
        overdue: (value: string) => `av dem ${value} uten kjent uke`,
        /** The SVG `<title>` (AD-18). [ASSUMPTION] */
        svg: "Kjedebånd: din del av kjeden. Ordre går mot venstre, varer mot høyre.",
        /** Information visibility (Story 6.21, UX-DR24): the end label of a neighbour whose numbers
         * show, «Distributør, Uke 11», and its numbers read after the Seat's own: «Distributør,
         * Uke 11: Lager 12, Restordre 3». [ASSUMPTION] */
        neighbour: (role: string, week: string) => `${role}, Uke ${week}`,
        neighbourRead: (label: string, numbers: string) => `${label}: ${numbers}`,
      },
    },
  },

  /** The Admin-område and its pages (FR-1–FR-3). «Brukere og roller» is EXPERIENCE.md's own. */
  admin: {
    /** The pages the Admin-område links to; later stories add theirs. */
    sections: {
      users: "Brukere og roller",
      // The working term «Institusjon» (EXPERIENCE.md → Terms, [ASSUMPTION]); Story 3.11.
      institutions: "Institusjoner",
      // [ASSUMPTION] Story 3.12.
      audit: "Revisjonslogg",
    },
    /** «Revisjonslogg» (Story 3.12, FR-3): every Admin action with who did it and when. The page
     * renders any action from these entries; a later epic adds its own action names here and the
     * page needs no other change. [ASSUMPTION] Story 3.12, all of it. */
    audit: {
      title: "Revisjonslogg",
      lead: "Hver handling i Admin-området, med hvem som gjorde den og når. Loggen kan ikke endres.",
      filters: {
        title: "Filtrer",
        actor: "Utført av",
        action: "Handling",
        all: "Alle",
        since: "Fra og med",
        until: "Til og med",
        rangeReversed: "Til og med-datoen kan ikke være før fra og med-datoen.",
      },
      list: {
        title: "Hendelser",
        columns: { time: "Tidspunkt", actor: "Utført av", action: "Handling", target: "Gjelder", change: "Endring" },
        empty: "Ingen hendelser ennå.",
        noMatches: "Ingen treff.",
        more: "Vis flere hendelser",
        moreFailed: "Flere hendelser kunne ikke lastes. Prøv igjen.",
      },
      /** «18. nov. 2026 kl. 13:01», Europe/Oslo. */
      at: (date: string, time: string) => `${date} kl. ${time}`,
      system: "Systemet",
      unknown: "Ukjent",
      noChange: "–",
      actions: {
        "invitation.sent": "Invitasjon sendt",
        "invitation.resent": "Invitasjon sendt på nytt",
        "invitation.accepted": "Invitasjon akseptert",
        "invitation.bootstrap": "Første Admin invitert",
        "role.bootstrap_granted": "Første Admin fikk rollen",
        "role.granted": "Rolle gitt",
        "role.revoked": "Rolle fjernet",
        "user.deactivated": "Bruker deaktivert",
        "user.reactivated": "Bruker aktivert igjen",
        "institution.created": "Institusjon opprettet",
        "institution.renamed": "Institusjon fikk nytt navn",
        // Story 3.13.
        "access_request.invited": "Invitert fra forespørsel",
        "access_request.dismissed": "Forespørsel avvist",
      } as Record<string, string>,
      /** What an action concerns, by its target key. */
      targets: {
        user_id: (label: string) => label,
        invitation_id: (label: string) => `Invitasjon til ${label}`,
        institution_id: (label: string) => label,
        access_request_id: (label: string) => `Forespørsel fra ${label}`,
      } as Record<string, (label: string) => string>,
      /** The labels of the change fields; an unknown field shows its own key. */
      fields: {
        role: "Rolle",
        account: "Konto",
        role_added: "Rollen lagt til",
        name: "Navn",
        old_name: "Gammelt navn",
        new_name: "Nytt navn",
        voided_invitation_ids: "Lenker gjort ugyldige",
      } as Record<string, string>,
      values: {
        roles: { lecturer: "Faglærer", admin: "Admin" } as Record<string, string>,
        account: { created: "Ny konto", existing: "Eksisterende konto" } as Record<string, string>,
        yes: "Ja",
        no: "Nei",
      },
    },
    /** «Institusjoner» (Story 3.11, FR-3): create and rename the Institutions Classes belong to.
     * [ASSUMPTION] Story 3.11, all of it. */
    institutions: {
      title: "Institusjoner",
      create: {
        title: "Ny Institusjon",
        lead: "Klasser hører til én Institusjon. Navnet kan endres senere, men en Institusjon kan ikke slettes.",
        name: "Navn",
        submit: "Opprett Institusjon",
        created: (name: string) => `${name} er opprettet.`,
        failed: "Institusjonen ble ikke opprettet. Prøv igjen.",
      },
      errors: {
        name_empty: "Skriv navnet på Institusjonen.",
        name_too_long: "Navnet kan ha høyst 200 tegn.",
        name_invalid: "Navnet kan ikke inneholde @ eller kontrolltegn.",
        institution_name_taken: "Det finnes allerede en Institusjon med dette navnet.",
      },
      list: {
        title: "Alle Institusjoner",
        columns: { name: "Navn", created: "Opprettet", actions: "Endre" },
        empty: "Ingen Institusjoner ennå. Opprett den første over.",
        more: "Vis flere Institusjoner",
        moreFailed: "Flere Institusjoner kunne ikke lastes. Prøv igjen.",
      },
      rename: {
        open: (name: string) => `Gi ${name} nytt navn`,
        field: (name: string) => `Nytt navn på ${name}`,
        save: "Lagre navnet",
        cancel: "Avbryt",
        renamed: (old: string, name: string) => `${old} heter nå ${name}.`,
        failed: "Navnet ble ikke endret. Prøv igjen.",
      },
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
          // [ASSUMPTION] Epic 3 review: the address of a deactivated User.
          accountDeactivated: "Kontoen med denne adressen er deaktivert. Aktiver den før du inviterer.",
        },
        // [ASSUMPTION] Story 3.7.
        failed: "Invitasjonen ble ikke sendt. Prøv igjen.",
        // [ASSUMPTION] Story 3.13: the form filled from a request for lecturer access.
        fromRequest: (name: string) => `Fyller inn fra forespørselen til ${name}.`,
      },
      /** The open requests for lecturer access from the Landing (Story 3.13, FR-1).
       * [ASSUMPTION] Story 3.13, all of it. */
      requests: {
        title: "Forespørsler om lærertilgang",
        lead: "Inviter fyller inn skjemaet over med adressen og rollen Faglærer. Ingenting sendes før du trykker Send Invitasjon.",
        columns: { name: "Navn", email: "E-post", institution: "Institusjon", received: "Mottatt", actions: "Endre" },
        invite: (name: string) => `Inviter ${name} som Faglærer`,
        dismiss: (name: string) => `Avvis forespørselen fra ${name}`,
        dismissed: (name: string) => `Forespørselen fra ${name} er avvist.`,
        dismissFailed: "Forespørselen ble ikke avvist. Prøv igjen.",
        // Another Admin answered it first; the list reads again without it.
        alreadyAnswered: (name: string) => `Forespørselen fra ${name} er allerede besvart.`,
        empty: "Ingen åpne forespørsler.",
        more: "Vis flere forespørsler",
        moreFailed: "Flere forespørsler kunne ikke lastes. Prøv igjen.",
      },
      /** The User list with its role buttons (Story 3.9, UX-DR57). «Ingen treff.» and the
       * blocked-revoke sentence are EXPERIENCE.md's and the epic's own; the rest is
       * [ASSUMPTION] Story 3.9. */
      list: {
        title: "Brukere",
        search: "Søk etter navn eller e-post",
        columns: { name: "Navn", email: "E-post", roles: "Roller", status: "Status", actions: "Endre" },
        roles: { lecturer: "Faglærer", admin: "Admin" },
        noRole: "Ingen rolle",
        active: "Aktiv",
        deactivated: "Deaktivert",
        noMatches: "Ingen treff.",
        more: "Vis flere",
        moreFailed: "Flere brukere kunne ikke lastes. Prøv igjen.",
        grant: (name: string, role: string) => `Gi ${name} rollen ${role}`,
        revoke: (name: string, role: string) => `Fjern rollen ${role} fra ${name}`,
        granted: (name: string, role: string) => `${name} har nå rollen ${role}.`,
        revoked: (name: string, role: string) => `${name} har ikke lenger rollen ${role}.`,
        blocked: (name: string, classes: number) =>
          classes === 1
            ? `${name} eier 1 Klasse. Legg til en annen Faglærer eller arkiver Klassen først.`
            : `${name} eier ${classes} Klasser. Legg til en annen Faglærer eller arkiver Klassene først.`,
        lastAdmin: (name: string) => `${name} er den eneste aktive Admin. Gi en annen bruker rollen Admin først.`,
        failed: "Rollen ble ikke endret. Prøv igjen.",
        // Story 3.10 (UX-DR57): the deactivate button states the consequence, in EXPERIENCE.md's
        // own words; the rest is [ASSUMPTION] Story 3.10.
        deactivate: (name: string) => `Deaktiver ${name}. ${name} kan ikke logge inn, og dataene blir værende.`,
        reactivate: (name: string) => `Aktiver ${name} igjen`,
        deactivatedLine: (name: string) => `${name} er deaktivert.`,
        reactivatedLine: (name: string) => `${name} er aktiv igjen.`,
        deactivateSelf: "Du kan ikke deaktivere deg selv.",
        statusFailed: "Statusen ble ikke endret. Prøv igjen.",
      },
      /** The Invitations sent, newest first, and resending one (Story 3.10, FR-1, FR-3).
       * [ASSUMPTION] Story 3.10, including the renewal-request line the epic asks this story to
       * write. */
      invitations: {
        title: "Invitasjoner",
        columns: { email: "E-post", role: "Rolle", status: "Status", expires: "Utløper", actions: "Send på nytt" },
        status: { open: "Åpen", accepted: "Akseptert", expired: "Utløpt" },
        renewalRequested: "Mottakeren har bedt om en ny invitasjon.",
        resend: (email: string) => `Send ny invitasjon til ${email}`,
        // [ASSUMPTION] Epic 3 review: the button's visible text; its name above keeps the address.
        resendShort: "Send ny invitasjon",
        // [ASSUMPTION] Epic 3 review: an accepted Invitation states when, in place of an expiry.
        acceptedOn: (date: string) => `Akseptert ${date}`,
        // [ASSUMPTION] Epic 3 review: why a row to a deactivated account has no resend.
        accountDeactivated: "Kontoen er deaktivert.",
        resent: (email: string, days: number) =>
          `Ny invitasjon sendt til ${email}. Den er gyldig i ${days === 1 ? "én dag" : `${days} dager`}.`,
        failed: "Invitasjonen ble ikke sendt på nytt. Prøv igjen.",
        deactivatedAccount: "Kontoen med denne adressen er deaktivert. Aktiver den før du sender på nytt.",
        empty: "Ingen invitasjoner ennå.",
        // Not «Vis flere» alone: the User list above has that button.
        more: "Vis flere invitasjoner",
        moreFailed: "Flere invitasjoner kunne ikke lastes. Prøv igjen.",
        months: ["jan.", "feb.", "mar.", "apr.", "mai", "jun.", "jul.", "aug.", "sep.", "okt.", "nov.", "des."],
      },
    },
  },

  /** The way into the Debrief (Story 9.2, FR-42, `07-debrief.png`): its page, step 1's heading and
   * the locked and held states. Shown before the Explanation is saved, so held to the pre-Debrief
   * copy rules (it is not one of POST_DEBRIEF_SECTIONS). «Skriv Forklaringen først» is the spine's;
   * the rest is [ASSUMPTION] draft copy. */
  debriefEntry: {
    /** «Debrief, Spill 17». */
    title: (number: number | null) => `Debrief, ${gameName(number)}`,
    /** «Grossist, Spill 17» under the title. */
    roleGame: (role: string, number: number | null) => `${role}, ${gameName(number)}`,
    /** Story 13.5: «Debrief, Oppfølgingsspill» and «Grossist, Oppfølgingsspill». [ASSUMPTION] */
    makeupTitle: "Debrief, Oppfølgingsspill",
    roleMakeup: (role: string) => `${role}, Oppfølgingsspill`,
    /** «Steg 1 av 5». */
    stepOf: (step: number, steps: number) => `Steg ${step} av ${steps}`,
    /** Step 1's heading (EXPERIENCE.md → Debrief sequence); steps 2 to 5 come with their
     * stories. */
    firstStep: "Skriv Forklaringen først",
    /** The page title before the Debrief is open. */
    locked: "Debrief",
    notOpen: "Debriefen åpner når Klassespillet ditt er ferdig.",
    held: "Debriefen åpner når alle Klassespillene er ferdige.",
    /** Step 1 (Story 9.3, EXPERIENCE.md → Debrief sequence, `07-debrief.png`). The chart title,
     * prompt, «Send Forklaring», «Vis som tabell» and the failure line are the spine's; the rest
     * is [ASSUMPTION] draft copy. Before the reveal: no customers, no demand. */
    explanation: {
      netTitle: "Ditt netto lager, hele spillet",
      showTable: "Vis som tabell",
      /** [ASSUMPTION] */
      showChart: "Vis som graf",
      netColumn: "Netto lager",
      /** [ASSUMPTION] */
      tableCaption: "Ditt netto lager i hver uke av spillet",
      /** [ASSUMPTION] */
      chartSvg: "Graf over ditt netto lager i hver uke av spillet: over null er lager, under null er restordre.",
      /** «Uke 1» and «Uke 36» at the ends of the x-axis. */
      week: (week: number) => `Uke ${week}`,
      prompt: "Hvorfor svingte lageret ditt?",
      /** [ASSUMPTION] who reads it, under the field. */
      hint: "Bare du og de som underviser Klassen, kan lese Forklaringen. Den kan ikke endres etter at du har sendt den.",
      send: "Send Forklaring",
      /** [ASSUMPTION] beside the field while it is empty. */
      empty: "Skriv Forklaringen før du sender.",
      failed: "Det ble ikke lagret. Prøv igjen.",
      /** [ASSUMPTION] */
      sentTitle: "Din Forklaring",
      /** [ASSUMPTION] */
      sent: "Forklaringen er sendt og lagret slik du skrev den.",
      /** [ASSUMPTION] a second device had already sent one. */
      exists: "Forklaringen var allerede sendt. Her er den som er lagret.",
      /** [ASSUMPTION] a step-1 read failed; «Prøv igjen» beside it. */
      loadFailed: "Dette steget kunne ikke hentes.",
    },
    /** The Group debrief (Story 9.11, FR-43, UX-DR31). The locked line is the spine's pattern
     * (EXPERIENCE.md → States: «Avsløringen er låst til alle fire har sendt. Ida og Mikkel har sendt,
     * Jonas skriver.»); the rest is [ASSUMPTION] draft copy. Before the reveal: no customers, no
     * demand. */
    group: {
      title: "Gruppedebrief",
      /** [ASSUMPTION] for a Student of the game who has not joined. */
      joinLead: "Gruppedebriefen for spillet ditt er i gang. Dere går gjennom de tre første stegene sammen, hver på sin egen enhet.",
      join: "Bli med i Gruppedebriefen",
      /** [ASSUMPTION] a failed join. */
      joinFailed: "Du ble ikke med. Prøv igjen.",
      notGroup: "Dette er en personlig debrief.",
      /** [ASSUMPTION] the time guide while writing, in a Group debrief. */
      timeGuide: "Sett av omtrent fem minutter til Forklaringen. Gruppen går videre når alle har sendt.",
      /** «begge», «alle tre», «alle fire»: how many joined Students must send. */
      everyone: (count: number) => (count === 2 ? "begge" : count === 3 ? "alle tre" : count === 4 ? "alle fire" : `alle ${count}`),
      /** «Avsløringen er låst til begge har sendt. Du har sendt, Jonas skriver.» */
      locked: (everyone: string, sent: string, writing: string) =>
        `Avsløringen er låst til ${everyone} har sendt. ${sent} har sendt, ${writing} skriver.`,
      /** The viewer in the locked and waiting lines. */
      you: "du",
      /** A joined Student no longer on the Roster. */
      someone: "en som ikke lenger er i Klassen",
      /** «Ida og Mikkel»: names joined with «og». */
      and: "og",
      /** [ASSUMPTION] a Student who has not sent while the group is further on. */
      behind: (step: number) => `Gruppen er på steg ${step}. Send Forklaringen, så kommer du rett dit.`,
      /** [ASSUMPTION] finishing a shared step. */
      done: "Ferdig med steget",
      /** «Du er ferdig. Venter på Jonas.» */
      waiting: (names: string) => `Du er ferdig. Venter på ${names}.`,
      /** [ASSUMPTION] the opener's control and when it is possible. */
      moveOn: "Gå videre for alle",
      moveOnAt: (time: string) => `Du kan flytte gruppen videre fra kl. ${time}, også om ikke alle er ferdige.`,
      tooEarly: (time: string) => `Gruppen kan gå videre fra kl. ${time}.`,
      failed: "Det ble ikke lagret. Prøv igjen.",
      /** Polite announcements when the shared step moves. */
      unlocked: "Alle har sendt. Avsløringen er åpen.",
      moved: (step: number) => `Gruppen er nå på steg ${step}.`,
      alone: "Gruppen har gått videre. Herfra svarer hver av dere på egen enhet.",
      /** [ASSUMPTION] Story 9.12: going on alone, from the join panel. */
      aloneLead: "Kan ikke gruppen møtes, går du gjennom Debriefen alene. Du kan ikke bli med i gruppen etterpå.",
      goAlone: "Ta en Personlig debrief",
      aloneFailed: "Det gikk ikke. Prøv igjen.",
      /** A join refused because the Student goes on alone (409 `group_closed`). */
      groupClosed: "Du går gjennom denne Debriefen alene.",
      /** [ASSUMPTION] leaving the group, with its confirmation in place. */
      leave: "Forlat gruppen",
      leaveConfirm: "Du fortsetter alene fra steget du er på, og det du har skrevet, er lagret. Du kan ikke bli med igjen.",
      cancel: "Avbryt",
      leaveFailed: "Du er fortsatt i gruppen. Prøv igjen.",
      /** [ASSUMPTION] why the Student goes on as a Personal debrief, under the step they were on. */
      aloneLine: {
        left: "Du går gjennom Debriefen alene, som en Personlig debrief. Det du har skrevet, er lagret.",
        dropout:
          "Du var borte fra Gruppedebriefen i mer enn to minutter, så gruppen gikk videre uten deg. Du fortsetter alene, som en Personlig debrief, fra steget du var på.",
        fallback:
          "Gruppedebriefen ble ikke ferdig innen 48 timer etter at spillet sluttet. Du fortsetter alene, som en Personlig debrief, fra steget du var på.",
        missed: "Gruppen har gått gjennom de felles stegene uten deg. Du går gjennom Debriefen alene, som en Personlig debrief.",
      },
      /** Story 9.13: the link to the shared screen, for a joined Student (UX-DR35). */
      sharedScreen: "Delt skjerm: hele kjeden",
    },
  },

  /** The Debrief after the reveal (Story 9.4 on, EXPERIENCE.md → Debrief sequence). Reached only
   * with a saved Explanation (the api gates it), so this is one of the copy check's
   * POST_DEBRIEF_SECTIONS and may name the exercise; `debriefEntry` above may not. */
  debrief: {
    /** The spine's prefix of every AI text in the Debrief (driven only by `ai_generated`, Story
     * 9.14); code-rendered text never carries it. */
    aiPrefix: "KI-generert, kan ta feil:",
    /** Story 9.14: an AI text as shown, «KI-generert, kan ta feil: «…»» (FR-34, UX-DR69). */
    aiText: (text: string) => `KI-generert, kan ta feil: «${text}»`,
    /** [ASSUMPTION] under an AI text: the AI may be wrong; every number is the code's (FR-44). */
    aiNote: "Teksten er satt sammen av en KI fra tallene i spillet ditt, og kan ta feil. Tallene er regnet ut av koden.",
    /** Step 2, the reveal of customer demand (`07-debrief.png`). Its heading comes from the api,
     * rendered from the demand series. «Ordre inn: det eneste du så», «Din ordre, 24 i Uke 11», the
     * table rows and «Øvelsen heter Beer Game.» are the spine's; the rest is [ASSUMPTION] draft. */
    reveal: {
      /** The Etterspørselsbånd's key, over the band. */
      demandKey: "Kundene",
      incomingKey: "Ordre inn: det eneste du så",
      orderKey: "Din ordre",
      /** On the band at its right end. */
      demandLabel: (demand: string) => `Kundenes etterspørsel: ${demand}`,
      /** At the Student's largest Order. */
      largestOrder: (order: string, week: number) => `Din ordre, ${order} i Uke ${week}`,
      /** [ASSUMPTION] the scroll region's name. */
      region: "Kundene, ordre inn og din ordre per uke",
      rows: { demand: "Kundene", incoming: "Ordre inn", order: "Din ordre" },
      /** [ASSUMPTION] */
      svg: "Kundenes etterspørsel som et bånd, ordrene som kom inn til deg som en linje og dine ordre som stolper, uke for uke.",
      /** [ASSUMPTION] */
      axisSvg: "Antall enheter",
      swipe: "Sveip for flere uker",
      named: "Øvelsen heter Beer Game.",
      /** [ASSUMPTION] what the Seat saw: the Role below it in the chain sent its orders
       * («ordrene fra Detaljisten»). */
      saw: (downstream: string) => `Det du så, var ordrene fra ${downstream}, ikke kundene.`,
      /** The Role, definite, for `saw`. */
      definite: { retailer: "Detaljisten", wholesaler: "Grossisten", distributor: "Distributøren", factory: "Fabrikken" },
      /** [ASSUMPTION] the Detaljist saw the customers, one Uke at a time. */
      sawRetailer: "Du så kundenes ordrer selv, men bare én uke om gangen.",
      /** [ASSUMPTION] from `07-debrief.png`, without names. */
      structure: "Nesten alle grupper svinger slik. Struktur gir atferd, derfor spør vi hvorfor og ikke hvem.",
      /** [ASSUMPTION] the step could not be read; «Prøv igjen» beside it. */
      loadFailed: "Avsløringen kunne ikke hentes.",
    },
    /** Step 3, the whole chain (Story 9.5, `07-debrief.png`, EXPERIENCE.md → Ukeskrubber). The
     * heading, «Kjeden i Uke 15. Dra i skrubberen for å spole.», «Velg uke», the step buttons,
     * the reading's form, «Produksjon», «Kundene» and Forsterkning are the spine's; the rest is
     * [ASSUMPTION] draft copy. */
    chain: {
      heading: "Hele kjeden: svingningene vokser oppstrøms og kommer senere",
      /** By the scrubber, with the chosen Uke. */
      at: (week: number) => `Kjeden i Uke ${week}. Dra i skrubberen for å spole.`,
      scrubber: "Velg uke",
      week: (week: number) => `Uke ${week}`,
      back: "Én uke tilbake",
      forward: "Én uke fram",
      /** The live reading, Fabrikk first: «Uke 15. Fabrikk: restordre 3, ordre 22. …». */
      reading: (week: number, roles: readonly string[]) => `Uke ${week}. ${roles.join(" ")}`,
      readingRole: (role: string, held: readonly string[], order: string) =>
        `${role}: ${[...held, `ordre ${order}`].join(", ")}.`,
      readingStock: (units: string) => `lager ${units}`,
      readingBacklog: (units: string) => `restordre ${units}`,
      /** [ASSUMPTION] the customers' order at the end of the reading. */
      readingCustomers: (order: string) => `Kundene: ordre ${order}.`,
      /** Band ends and node numbers. */
      production: "Produksjon",
      customers: "Kundene",
      stock: (units: string) => `Lager ${units}`,
      backlog: (units: string) => `Restordre ${units}`,
      /** [ASSUMPTION] the band's key: what the numbers in the gaps are. */
      bandKey: "Øverst: ordre, som går mot venstre. Over røret: på vei, som går mot høyre.",
      /** [ASSUMPTION] */
      bandSvg: "Hele kjeden i den valgte uka: lager og restordre for hver rolle, ordre og varer på vei mellom dem.",
      /** [ASSUMPTION] a capped Role (FEATURE_CAPACITY, Story 6.22). */
      capacity: (role: string, units: string) => `${role} kan sende høyst ${units} enheter per uke.`,
      /** [ASSUMPTION] the Ordrestolper region's name and key. */
      region: "Ordre per rolle og uke",
      /** With the api's `large_order` (10). */
      barsKey: (large: string) =>
        `Ordre per rolle og uke, som stolpe og som tall i samme kolonne. Rødt punkt: første uke med ordre på ${large} eller mer. Til høyre: Forsterkning.`,
      amplification: "Forsterkning",
      /** «(deg)» after the own Role, as in Kjedens regning. */
      own: "(deg)",
      /** [ASSUMPTION] no Forsterkning when the customers' demand never varied. */
      none: "–",
      /** [ASSUMPTION] Forsterkning as one line of text, Detaljist first. */
      amplificationLine: (parts: readonly string[]) => `Forsterkning fra kundene og oppover: ${parts.join(", ")}.`,
      amplificationPart: (role: string, value: string) => `${role} ${value}`,
      /** [ASSUMPTION] */
      barsSvg: "Ordrestolper: ordrene til hver rolle uke for uke, Fabrikk øverst, med første store ordre markert.",
      /** [ASSUMPTION] */
      barsAxisSvg: "Rollene, Fabrikk øverst",
      swipe: "Sveip for flere uker",
      /** [ASSUMPTION] the step could not be read; «Prøv igjen» beside it. */
      loadFailed: "Kjeden kunne ikke hentes.",
    },
    /** «Delt skjerm: hele kjeden» (Story 9.13, FR-74, UX-DR34, UX-DR35, `07-debrief.png`): the
     * group's charts by Role on one screen in the room. Never a name. The title, «Netto lager»,
     * «Kostnad, kr» and the direction line are the spine's; the rest is [ASSUMPTION] draft copy. */
    shared: {
      title: "Delt skjerm: hele kjeden",
      /** «Spill 17» under the title. */
      game: (number: number | null) => gameName(number),
      /** Where the group is, by the shared step pointer. */
      step: (step: number, individual: number, steps: number) =>
        step >= individual
          ? "Gruppen har gått gjennom de felles stegene. Nå svarer hver på sin egen enhet."
          : `Gruppen er på steg ${step} av ${steps}. Hver svarer på sin egen enhet.`,
      /** [ASSUMPTION] while a joined Student has not sent: no names, no counts. */
      locked: "Avsløringen er låst til alle i gruppen har sendt Forklaringen. Kjeden vises her når den åpner.",
      /** [ASSUMPTION] polite, when the lock opens on this screen. */
      unlocked: "Alle har sendt. Kjeden vises nå.",
      /** By the scrubber, with the chosen Uke. */
      at: (week: number) => `Kjeden i Uke ${week}.`,
      /** [ASSUMPTION] who controls the scrubber (UX-DR34). */
      scrubberNote: "Skrubberen styres bare fra denne skjermen. Hver telefon har sin egen.",
      netTitle: "Netto lager",
      costTitle: "Kostnad, kr",
      /** [ASSUMPTION] */
      netSvg: (role: string) => `Graf over netto lager for ${role} i hver uke: over null er lager, under null er restordre.`,
      showTable: "Vis som tabell",
      showChart: "Vis som graf",
      /** [ASSUMPTION] the Netto lager table's caption. */
      netCaption: "Netto lager per rolle og uke",
      /** [ASSUMPTION] the band's text alternative at the chosen Uke. */
      bandCaption: (week: number) => `Kjeden i Uke ${week}: lager, restordre, på vei og ordre per rolle`,
      columns: { role: "Rolle", stock: "Lager", backlog: "Restordre", supplyLine: "På vei", order: "Ordre" },
      /** Under the charts (`07-debrief.png`). */
      direction:
        "Gruppen ser hele kjeden på storskjermen, i samme retning som på telefonen: varene går mot høyre, ordrene mot venstre. Hver student følger sitt eget steg på telefonen.",
      back: "Tilbake til Debriefen",
      /** [ASSUMPTION] the screen could not be read; «Prøv igjen» beside it. */
      loadFailed: "Den delte skjermen kunne ikke hentes.",
    },
    /** The reflection questions between steps 3 and 4 (Story 9.6, FR-45, EXPERIENCE.md → Debrief
     * sequence: not drawn). The questions are content from the api; «Det ble ikke lagret. Prøv
     * igjen.» is the spine's; the rest is [ASSUMPTION] draft copy. */
    reflection: {
      /** [ASSUMPTION] unnumbered: the spine's five steps keep their numbers. */
      heading: "Spørsmål til ettertanke",
      /** [ASSUMPTION] «Spørsmål 2 av 3». */
      counter: (at: number, of: number) => `Spørsmål ${at} av ${of}`,
      /** [ASSUMPTION] who reads the answers, under the field (FR-58 adds the report's line). */
      privacy: "Bare du og de som underviser Klassen, kan lese svarene. Et svar kan ikke endres etter at du har gått videre.",
      /** [ASSUMPTION] */
      next: "Fortsett",
      /** [ASSUMPTION] beside the field while it is empty. */
      empty: "Skriv et svar før du går videre.",
      failed: "Det ble ikke lagret. Prøv igjen.",
      /** [ASSUMPTION] a second device answered further already: the page shows where it stands. */
      outOfOrder: "Dette spørsmålet var allerede besvart. Her er neste.",
      /** [ASSUMPTION] a second device answered this question first: its stored answer stays. */
      answeredElsewhere: "Spørsmålet var allerede besvart på en annen enhet. Svaret som er lagret, står over.",
      /** [ASSUMPTION] over each stored answer. */
      answered: "Ditt svar",
      /** [ASSUMPTION] once every question is answered. */
      done: "Du har svart på alle spørsmålene. Svarene er lagret slik du skrev dem.",
      /** [ASSUMPTION] the questions could not be read; «Prøv igjen» beside it. */
      loadFailed: "Spørsmålene kunne ikke hentes.",
    },
    /** Follow-up questions about the Student's own Game, under the reflection questions (Story
     * 9.15, FR-45, UX-DR31). Spine-only surface: all [ASSUMPTION] draft. */
    followUp: {
      /** [ASSUMPTION] */
      heading: "Spør om spillet ditt",
      /** [ASSUMPTION] what an answer is, before the field. */
      intro: "Lurer du på noe om spillet ditt? Du får hint om hvor du kan se, ikke svar.",
      /** [ASSUMPTION] the field's label. */
      label: "Spørsmålet ditt",
      /** [ASSUMPTION] under the field: who reads it, and the KI. */
      privacy: "Spørsmålet sendes til en KI, med navn og e-postadresser fjernet. Det lagres sammen med svaret.",
      /** [ASSUMPTION] */
      send: "Spør",
      /** [ASSUMPTION] while the answer is on its way. */
      sending: "Venter på svar …",
      /** [ASSUMPTION] beside the button while the field is empty. */
      empty: "Skriv et spørsmål først.",
      /** [ASSUMPTION] over each earlier question. */
      asked: "Du spurte",
      /** [ASSUMPTION] a question outside the Game: the fixed line, never the KI's words. */
      declined: "Det spørsmålet handler ikke om spillet ditt. Spør om ukene, bestillingene eller kostnadene dine.",
      /** [ASSUMPTION] no answer could be given; the question stays in the field. */
      unanswered: "Det kom ikke noe svar denne gangen. Spørsmålet står igjen i feltet, så du kan prøve igjen eller gå videre.",
      /** [ASSUMPTION] too many questions (from this account or this network): the wait, in whole
       * minutes. */
      rateLimited: (minutes: number) =>
        minutes <= 1
          ? "Det er sendt mange spørsmål på kort tid. Vent ett minutt før du spør igjen."
          : `Det er sendt mange spørsmål på kort tid. Vent ${minutes} minutter før du spør igjen.`,
      /** [ASSUMPTION] the field is gone: the Individual test has opened or the Testfrist passed. */
      closed: "Spørsmål om spillet er stengt nå.",
      /** [ASSUMPTION] */
      failed: "Spørsmålet ble ikke sendt. Prøv igjen.",
      /** [ASSUMPTION] the list could not be read; «Prøv igjen» beside it. */
      loadFailed: "Spørsmålene dine kunne ikke hentes.",
    },
    /** Step 4, the own moments (Story 9.7, `07-debrief.png`). The heading and each moment's
     * sentences come from the api, rendered by code from the facts. «Dette så du», «Dette regnet
     * du», «Dette kostet det senere» and «Dette så de andre i Uke N» are the spine's; the rest is
     * [ASSUMPTION] draft. */
    moments: {
      /** [ASSUMPTION] the step's heading with no moments (mostly AI players). */
      heading: "Dine øyeblikk",
      /** [ASSUMPTION] fewer than 10 own Orders (FR-44). */
      mostlyAi:
        "Klassespillet ditt ble spilt mest av KI-spillere, så her er ingen øyeblikk fra din egen plass. Dine egne øyeblikk finner du i Replay.",
      /** [ASSUMPTION] under it: steps 2 and 3 hold for this Student too. */
      mostlyAiChain: "Kundene og hele kjeden over gjelder spillet ditt som for alle andre.",
      /** [ASSUMPTION] «Øyeblikk 1 av 3», the heading focus moves to. */
      counter: (at: number, of: number) => `Øyeblikk ${at} av ${of}`,
      /** [ASSUMPTION] the paging buttons. */
      previous: "Forrige øyeblikk",
      next: "Neste øyeblikk",
      /** [ASSUMPTION] the paging group's name. */
      paging: "Bla mellom øyeblikkene",
      saw: "Dette så du",
      reckoned: "Dette regnet du",
      later: "Dette kostet det senere",
      others: (week: number) => `Dette så de andre i Uke ${week}`,
      /** [ASSUMPTION] the others table's role column. */
      role: "Rolle",
      /** [ASSUMPTION] the pattern block's label. */
      pattern: "Mønster i uka",
      /** [ASSUMPTION] the Graf over tabell region's name for the moment's Uke. */
      region: (week: number) => `Graf og tabell fram til Uke ${week}`,
      /** [ASSUMPTION] the own Explanation beside the data (FR-44, FR-41). */
      explanation: "Din Forklaring",
      /** [ASSUMPTION] */
      explanationNote: "Det du skrev før avsløringen, slik du sendte den.",
      /** [ASSUMPTION] the moments could not be read; «Prøv igjen» beside it. */
      loadFailed: "Øyeblikkene kunne ikke hentes.",
      /** [ASSUMPTION] Story 9.14: the label of the line that ties the moments together. */
      narration: "Øyeblikkene sammen",
    },
    /** The end of step 4: Kjedens regning with the Debrief's rows and lines, and «Fullfør
     * Debriefen» (Story 9.8, UX-DR36, EXPERIENCE.md → Debrief). «Simulert, samme kunder», the
     * restordre line and «Simulert viser sammenhengen, ikke en fasit.» are the spine's (with «du»
     * for the viewer's name); the rest is [ASSUMPTION] draft copy. */
    bill: {
      simulated: "Simulert, samme kunder",
      simulatedOwn: "Bare du teller på vei",
      simulatedAll: "Alle fire teller på vei",
      simulatedNote: "Simulert viser sammenhengen, ikke en fasit.",
      /** [ASSUMPTION] how the simulated rows were played. */
      simulatedRule:
        "Samme kunder og samme kjede, spilt med én fast regel for alle fire roller. En rolle som teller på vei, regner med det den har bestilt og ikke fått ennå.",
      shareDouble: (percent: number) => `Restordre er ${percent} % av kjedens regning, fordi den koster dobbelt.`,
      /** [ASSUMPTION] when backlog does not cost twice inventory. */
      share: (percent: number) => `Restordre er ${percent} % av kjedens regning.`,
      /** [ASSUMPTION] the AI-held share (FR-44), under Kjedens regning. */
      aiShare: (percent: number, kroner: string) =>
        `${percent} % av kjedens regning, ${kroner}, kom i uker der en KI-spiller hadde et sete.`,
      /** [ASSUMPTION] */
      finish: "Fullfør Debriefen",
      /** [ASSUMPTION] above the button. */
      finishHint: "Når du fullfører, lagres Debriefen din. Du kan lese alt igjen etterpå, men ingenting kan endres.",
      /** [ASSUMPTION] once finished, with «ti. 24. nov. kl. 10:00». */
      finished: (when: string) => `Debriefen er fullført ${when}. Du kan lese alt igjen, men ingenting kan endres.`,
      /** [ASSUMPTION] 409 `debrief_incomplete`. */
      incomplete: "Svar på alle spørsmålene og les øyeblikkene før du fullfører.",
      /** [ASSUMPTION] 409 `test_deadline_passed`. */
      deadlinePassed: "Testfristen er passert, så Debriefen kan ikke fullføres lenger.",
      failed: "Det ble ikke lagret. Prøv igjen.",
      /** [ASSUMPTION] the bill could not be read; «Prøv igjen» beside it. */
      loadFailed: "Kjedens regning kunne ikke hentes.",
      /** [ASSUMPTION] whether the Debrief is finished could not be read; «Prøv igjen» beside it. */
      summaryFailed: "Det kunne ikke hentes om Debriefen er fullført.",
    },
    /** A Student's Explanation and Debrief summary for the Class's staff (Story 9.8, FR-47),
     * reached from Spillinnsikt. All [ASSUMPTION] draft copy. */
    staffSummary: {
      title: "Debrief-sammendrag",
      crumb: "Debrief-sammendrag",
      explanation: "Forklaring",
      noExplanation: "Studenten har ikke sendt Forklaringen ennå.",
      sentAt: (when: string) => `Sendt ${when}.`,
      summary: "Debriefen",
      notFinished: "Studenten har ikke fullført Debriefen ennå.",
      finishedAt: (when: string) => `Fullført ${when}.`,
      late: "Det var etter Debrief-fristen.",
      moments: "Øyeblikk",
      noMoments: "Ingen egne øyeblikk: Klassespillet ble spilt mest av KI-spillere.",
      reflection: "Spørsmål til ettertanke",
      noStudent: "Studenten har ikke noe Klassespill i denne Klasseøkten.",
      /** Story 9.10: the Student's name is read from the Roster now; gone once removed. [ASSUMPTION] */
      removed: "Studenten er ikke lenger i Klassen.",
      /** Story 9.10 (FR-46, FR-47): the Student's Debrief quiz attempts. [ASSUMPTION] */
      quiz: "Debrief-quiz",
      noAttempts: "Studenten har ikke tatt quizen ennå.",
      attempts: (n: number) => (n === 1 ? "1 forsøk." : `${n} forsøk.`),
      passedAt: (when: string) => `Bestått ${when}.`,
      notPassed: "Ikke bestått ennå.",
      /** One attempt: «Forsøk 2, to. 26. nov. kl. 14:15: bestått». */
      attempt: (n: number, when: string, passed: boolean) =>
        `Forsøk ${n}, ${when}: ${passed ? "bestått" : "ikke bestått"}`,
    },
    /** Story 9.10 (FR-46, UX-DR12): the Klasseøkt's «Debrief-quiz» block, where the Faglærer takes
     * a question out. Draft copy, [ASSUMPTION]. */
    quizExclusions: {
      heading: "Debrief-quiz",
      help: "Et spørsmål du tar ut, stilles ikke i studentenes neste forsøk. Gjelder alle studentene i denne Klasseøkten fram til Testfristen. Ingen blir bestått av endringen, og en student som har bestått, forblir bestått.",
      /** Before the lock: the version the lock will pin. */
      latest: "Quizen låses ved startdatoen. Til da vises den nyeste versjonen.",
      placeholder: "Spørsmålene er foreløpige og byttes ut før kurset tar dem i bruk.",
      /** «Spørsmål 1 av 3». */
      questionOf: (n: number, total: number) => `Spørsmål ${n} av ${total}`,
      answer: (text: string) => `Riktig svar: ${text}`,
      /** The Bryter's state text. */
      included: "Med i quizen",
      excluded: "Tatt ut",
      save: "Lagre quizvalg",
      saving: "Lagrer …",
      saved: "Quizvalgene er lagret.",
      /** Read-only reasons. */
      assistant: "Bare Faglærerne i Klassen kan ta ut spørsmål.",
      closed: "Testfristen er passert, så quizvalgene kan ikke endres lenger.",
      /** Refusals beside «Lagre quizvalg». */
      lastQuestion: "Minst ett spørsmål må være med i quizen.",
      deadlinePassed: "Testfristen er passert, så quizvalgene kan ikke endres lenger.",
      archived: "Klassen er arkivert, så quizvalgene kan ikke endres.",
      failed: "Quizvalgene ble ikke lagret. Prøv igjen.",
      loadFailed: "Debrief-quizen kunne ikke hentes.",
    },
    /** Step 5, the Debrief quiz (Story 9.9, FR-46, UX-DR37). «Debrief-quiz» is the spine's; the
     * rest is [ASSUMPTION] draft copy. The marks on each row are `quizChoice`'s. */
    quiz: {
      heading: "Debrief-quiz",
      intro:
        "Velg ett svar på hvert spørsmål. Du kan prøve så mange ganger du vil fram til Testfristen. Quizen teller ikke på noen karakter.",
      /** While the quiz content is a placeholder (issue #16). */
      placeholder: "Spørsmålene er foreløpige og byttes ut før kurset tar dem i bruk.",
      /** Over the questions of an attempt. */
      attempt: (n: number) => `Forsøk ${n}`,
      /** «Spørsmål 1 av 3», before each question. */
      questionOf: (n: number, total: number) => `Spørsmål ${n} av ${total}`,
      send: "Send svarene",
      /** Beside «Send svarene» while a question has no choice. */
      unanswered: "Velg et svar på hvert spørsmål før du sender.",
      /** «Forsøk 2: 2 av 3 riktige.» The result summary, focused after a send. */
      result: (attempt: number, correct: number, asked: number) => `Forsøk ${attempt}: ${correct} av ${asked} riktige.`,
      retryHint: "Les forklaringene og prøv igjen. Spørsmålene kan komme i en annen rekkefølge.",
      retry: "Prøv igjen",
      passed: (attempts: number) =>
        attempts === 1
          ? "Alle svarene er riktige. Quizen er bestått på første forsøk."
          : `Alle svarene er riktige. Quizen er bestått etter ${attempts} forsøk.`,
      /** 409 `test_deadline_passed`. */
      deadlinePassed: "Testfristen er passert, så svarene kan ikke sendes lenger.",
      /** 409 `quiz_passed`: another device passed it first. */
      alreadyPassed: "Quizen er allerede bestått.",
      failed: "Svarene ble ikke sendt. Prøv igjen.",
      /** The quiz could not be read; «Prøv igjen» beside it. */
      loadFailed: "Quizen kunne ikke hentes.",
    },
  },

  /** The Replay after the Debrief (Epic 10). */
  replay: {
    /** Replay-gjennomgang (Story 10.7, FR-50, UX-DR64, EXPERIENCE.md → Replay-gjennomgang,
     * `09-alle-sider.png`). «Gjennomgangen lages.» and «Ikke like for like.» are the spine's; every
     * other line is [ASSUMPTION] draft copy (open-assumptions.md). No line ranks, praises or says
     * which run was better (UX-DR72). */
    walkthrough: {
      title: "Replay-gjennomgang",
      roleReplay: (role: string) => `${role}, Replay`,
      pending: "Gjennomgangen lages.",
      totalLabel: "Totalkostnad, Replay",
      classTotalLabel: (number: number | null) =>
        number === null ? "Totalkostnad, Klassespillet" : `Totalkostnad, Klassespillet (${gameName(number)})`,
      chartTitle: "Netto lager, Replay og Klassespillet på samme ukeakse",
      chartTitleAlone: "Netto lager, Replay",
      legend: "Farget linje og flate: Replay. Grå linje: Klassespillet.",
      chartSvg: "Graf over netto lager i hver uke: Replay med farget linje, Klassespillet med grå linje.",
      chartSvgAlone: "Graf over netto lager i hver uke av Replay.",
      week: (week: number) => `Uke ${week}`,
      showTable: "Vis som tabell",
      showChart: "Vis som graf",
      tableCaption: "Replay og Klassespillet uke for uke: netto lager, din ordre og kostnad så langt, i kroner",
      tableCaptionAlone: "Replay uke for uke: netto lager, din ordre og kostnad så langt, i kroner",
      columnNet: (run: string) => `Netto lager, ${run}`,
      /** «Ordre», not «Din ordre»: in the Class game a KI-spiller may have ordered for the Seat. */
      columnOrder: (run: string) => `Ordre, ${run}`,
      columnCost: (run: string) => `Kostnad så langt, ${run}`,
      /** A cell of an Uke the shorter run did not have. */
      noWeek: "–",
      runReplay: "Replay",
      runClass: "Klassespill",
      /** «Ikke like for like.» and why, in words (FR-50, UX-DR70). */
      unlike: "Ikke like for like.",
      unlikeNeighbours: "I Replay var de tre andre Rollene KI-spillere.",
      unlikeDemand: "Kundene etterspurte andre mengder enn i Klassespillet.",
      unlikeWeeks: (replay: number, klass: number) =>
        replay === klass ? `Begge hadde ${replay} uker.` : `Replay hadde ${replay} uker, Klassespillet ${klass}.`,
      mostlyAi: "Klassespillet ditt ble spilt mest av KI-spillere, så det står ikke ved siden av Replay her.",
      momentsTitle: "Øyeblikk fra din Replay",
      narration: "Slik henger øyeblikkene sammen",
      noMoments: "Replay hadde for få av dine egne ordrer til å velge øyeblikk.",
      reckoned: "Dette regnet du",
      later: "Dette kostet det senere",
      pattern: "Mønster",
      /** The Replay has not finished: no walkthrough yet. */
      notFinished: "Gjennomgangen kommer når Replay er ferdig.",
      toReplay: "Til Replay",
      loadFailed: "Gjennomgangen kunne ikke hentes.",
    },
    /** The two optional questions after the walkthrough (Story 10.8, FR-50, FR-70); the
     * believability one is `nb.believability`. [ASSUMPTION] draft copy (open-assumptions.md). */
    questions: {
      title: "Frivillige spørsmål",
      anotherRound: "Ville du spilt en runde til?",
      yes: "Ja",
      no: "Nei",
      send: "Send svar",
      /** The button's accessible name: its visible words first, then its question (WCAG 2.5.3). */
      sendName: "Send svar om en runde til",
      saved: (yes: boolean) => (yes ? "Takk. Du svarte ja." : "Takk. Du svarte nei."),
      failed: "Svaret ble ikke sendt. Prøv igjen.",
    },
  },

  /** Quizvalg's marks on a scored question (UX-DR37): in text, never by colour alone. The spine's
   * words. */
  quizChoice: {
    wrong: "Ditt svar, ikke riktig",
    right: "Riktig",
  },

  /** The believability question (Story 10.8, FR-70, UX-DR76): on «Spillet er ferdig» after a
   * Class game with an AI player, and after the Replay-gjennomgang. Optional, never blocking; the
   * answer is never shown to staff beside a name. Every line is [ASSUMPTION] draft copy
   * (open-assumptions.md). */
  believability: {
    title: "Et frivillig spørsmål",
    legend: "Hvor troverdige var KI-spillernes ordrer?",
    /** The end points of the five-point scale, in words. */
    low: "1: ikke troverdige",
    high: "5: svært troverdige",
    note: "Frivillig. Faglærerne ser aldri svaret ditt med navnet ditt.",
    send: "Send svar",
    /** The button's accessible name: its visible words first, then its question (WCAG 2.5.3). */
    sendName: "Send svar om troverdighet",
    saved: (rating: number) => `Takk. Du svarte ${rating} av 5.`,
    failed: "Svaret ble ikke sendt. Prøv igjen.",
  },

  /** The AI assessment (Epic 12). */
  tests: {
    /** Story 11.3 (FR-51, UX-DR65, EXPERIENCE.md → Individuell test): the Student's test page.
     * The locked line and «Testfristen er passert. Testen er ikke levert.» are the spine's; the
     * own-work statement, its button and the item lines are [ASSUMPTION] draft copy for the
     * founder's review. */
    individual: {
      title: "Individuell test",
      statementHeading: "Eget arbeid",
      statement:
        "Svarene i testen skal være ditt eget arbeid. Du svarer selv og lar ingen andre svare for deg.",
      howItWorks: "Du kan lukke testen og fortsette senere. Svarene lagres underveis, og du leverer én gang.",
      /** «Testfrist to. 18. des. kl. 23:59.» */
      deadline: (date: string) => `Testfrist ${date}.`,
      /** The one primary button, named by its effect (UX-DR9). */
      accept: "Bekreft og åpne testen",
      failed: "Testen ble ikke åpnet. Prøv igjen.",
      errors: {
        test_deadline_passed: "Testfristen er passert. Testen er ikke levert.",
        replay_required: "Individuell test, åpnes når du har fullført Replay.",
      },
      closed: "Testfristen er passert. Testen er ikke levert.",
      itemsHeading: "Oppgavene",
      /** «Oppgave 3». */
      item: (n: number) => `Oppgave ${n}`,
      types: {
        choice: "Flervalg",
        table: "Fyll inn kolonnen",
        number: "Tallsvar",
        long: "Langsvar",
        /** [ASSUMPTION] a drawn Interactive item (Story 11.14): points in a graph over its table. */
        drawn: "Tegn i grafen",
        /** [ASSUMPTION] an Adapted item (Story 11.7): asked about the Student's own game or Replay,
         * answered as a long answer. The Klasseøkt calls these «Tilpassede oppgaver». */
        adapted: "Tilpasset oppgave",
      },
      /** Autosave (Story 11.4, UX-DR65): «Lagret 21:14», Europe/Oslo; the failure line is the
       * spine's. */
      saved: (time: string) => `Lagret ${time}`,
      notSaved: "Ikke lagret. Svarene ligger på denne enheten, og vi prøver igjen.",
      /** [ASSUMPTION] draft copy: a choice item's option, while the draft question set has option
       * ids only (the real texts are issue #16's deliverable). «Alternativ B». */
      option: (id: string) => `Alternativ ${id.toUpperCase()}`,
      /** [ASSUMPTION] draft copy: a save the api refused; it is not tried again. */
      saveErrors: {
        attempt_submitted: "Testen er levert. Svaret ble ikke lagret.",
        test_deadline_passed: "Testfristen er passert. Svaret ble ikke lagret.",
        /** [ASSUMPTION] Story 11.12: the timed sitting ended before the save arrived. */
        sitting_ended: "Tiden er ute. Svaret ble ikke lagret.",
      } as Readonly<Record<string, string>>,
      saveRefused: "Svaret ble ikke lagret. Last siden på nytt.",
      /** Table and number Interactive items (Story 11.5, FR-80, UX-DR38). «Skriv et helt tall.»
       * and «Ikke besvart» are the spine's; the rest is [ASSUMPTION] draft copy. */
      interactive: {
        /** [ASSUMPTION] above each Interactive item (FR-80, UX-DR74): these items are hard. */
        intro: "Oppgaver som dette er vanskelige, også for voksne med lang utdanning. Ta én uke om gangen.",
        /** [ASSUMPTION] the heading over the row labels of a value table. */
        rowHeader: "Uke",
        /** Beside the row label of an Uke with no value. */
        notAnswered: "Ikke besvart",
        /** [ASSUMPTION] a cell's name: «Lager, Uke 3». */
        cell: (asked: string, row: string) => `${asked}, ${row}`,
        wholeNumber: "Skriv et helt tall.",
      },
      /** A drawn Interactive item (Story 11.14, FR-80, UX-DR38): points in a graph over its value
       * table, one answer. «Uke 3: 14 enheter» is the spine's; the rest is [ASSUMPTION] draft copy. */
      drawn: {
        /** Under the prompt: the three ways to answer, and that the table is the answer. */
        howTo: "Dra eller trykk i grafen, bruk piltastene, eller skriv i tabellen. Grafen og tabellen er samme svar.",
        /** The scroll region that holds the graph and its table. */
        region: (caption: string) => `Graf og tabell: ${caption}`,
        /** The group of points: the graph is a view of the table under it. */
        graph: "Graf over tabellen",
        /** A point's value as a slider reads it. */
        valueText: (week: string, value: string, n: number) => `${week}: ${value} ${n === 1 || n === -1 ? "enhet" : "enheter"}`,
        notAnsweredText: (week: string) => `${week}: ikke besvart`,
        /** The SVGs' titles (AD-18). */
        svg: (caption: string) => `Graf: ${caption}`,
        axisSvg: "Verdiene på grafens akse",
        /** [ASSUMPTION] as the charts' line: shown while later Uker are out of view. */
        swipe: "Sveip for flere uker",
      },
      /** Long answers (Story 11.6, FR-73, UX-DR65). [ASSUMPTION] draft copy: the advice shown
       * above the field on a phone. */
      long: {
        largerScreen: "Langsvar er lettere å skrive på en større skjerm, som en PC. Du kan likevel skrive og lagre her.",
        /** [ASSUMPTION] draft copy: the count shown once the text nears the longest answer. */
        count: (used: string, max: string) => `${used} av ${max} tegn`,
        /** [ASSUMPTION] draft copy: pasted text went past the longest answer and was cut. */
        cut: (max: string) => `Svaret kan være på høyst ${max} tegn. Det som gikk over, ble ikke tatt med.`,
      },
      /** Review and submit (Story 11.10, FR-51, UX-DR65, UX-DR59). «Lever testen», the unanswered
       * line, the warning, «Levert …» and the failure line are the spine's; the rest is
       * [ASSUMPTION] draft copy. */
      submit: {
        /** The one primary button, under the items and again in the review. */
        button: "Lever testen",
        /** [ASSUMPTION] the review's heading. */
        reviewHeading: "Gå gjennom før du leverer",
        /** «3 oppgaver er ikke besvart:», followed by the item numbers as links. */
        unanswered: (n: number) => (n === 1 ? "1 oppgave er ikke besvart:" : `${n} oppgaver er ikke besvart:`),
        /** Between the numbers: «4, 7 og 9». */
        listComma: ", ",
        listAnd: " og ",
        listEnd: ".",
        /** The link text of one unanswered item, for a screen reader: «Oppgave 4». */
        itemLink: (n: number) => `Oppgave ${n}`,
        /** [ASSUMPTION] every item answered. */
        allAnswered: "Alle oppgavene er besvart.",
        warning: "Du kan ikke endre svarene etter at du har levert.",
        /** [ASSUMPTION] while an answer typed on this device is not yet stored. */
        saving: "Svarene lagres …",
        failed: "Det ble ikke lagret. Prøv igjen.",
        errors: {
          /** [ASSUMPTION] the Testfrist passed while the page was open. */
          test_deadline_passed: "Testfristen er passert. Svarene du har lagret, leveres automatisk.",
          /** [ASSUMPTION] Story 11.12: the timed sitting ended while the review was open. */
          sitting_ended: "Tiden er ute. Svarene du har lagret, leveres automatisk.",
        } as Readonly<Record<string, string>>,
        /** «Levert to. 18. des. kl. 21:40. Du kan ikke endre svarene.» */
        submitted: (date: string) => `Levert ${date}. Du kan ikke endre svarene.`,
        /** Story 11.11's state: handed in by the Testfrist. */
        autoSubmitted: "Testfristen er passert. Svarene dine ble levert automatisk.",
        /** [ASSUMPTION] the heading over the read-only answers. */
        answersHeading: "Svarene dine",
        /** [ASSUMPTION] a read-only answer: «Ditt svar: Alternativ B», «Legg til: 16». */
        yourAnswer: "Ditt svar",
        answerLine: (label: string, value: string) => `${label}: ${value}`,
      },
      /** One timed sitting (Story 11.12, FR-51, UX-DR65). «Tid igjen 38 min», «5 minutter igjen.
       * Svarene dine er lagret.» and «Tiden er ute. Testen er levert.» are the epic's draft copy;
       * the rest is [ASSUMPTION] draft copy for the founder's review. */
      timed: {
        /** In the own-work statement, before the button (UX-DR9). */
        limit: (minutes: number) =>
          `Testen har en tidsgrense på ${minutes} minutter. Tiden starter når du åpner testen, og den kan ikke stoppes.`,
        /** Replaces «Du kan lukke testen og fortsette senere …» for a timed sitting. */
        howItWorks:
          "Svarene lagres underveis. Lukker du testen, går tiden likevel, og du kan komme tilbake før tiden er ute.",
        /** Fixed at the top of the open test, in whole minutes. */
        timeLeft: (minutes: number) => `Tid igjen ${minutes} min`,
        /** Announced politely once. */
        fiveMinutes: "5 minutter igjen. Svarene dine er lagret.",
        /** The sitting ended: before the sweep, and once it has handed the test in. */
        ended: "Tiden er ute. Testen er levert.",
      },
    },
    /** Story 11.12 (FR-51, UX-DR12, UX-DR49): the Klasseøkt's block «Tidsgrense» for the
     * Individual test, saved with «Lagre Klasseøkt». [ASSUMPTION] draft copy for the founder's
     * review. */
    sitting: {
      heading: "Tidsgrense på testen",
      lead: "Studentene kan ta Individuell test over flere kvelder fram til testfristen, eller i én økt med tidsgrense.",
      /** The Bryter's state words. */
      on: "Én økt med tidsgrense",
      off: "Ingen tidsgrense",
      minutesLabel: "Tidsgrense i minutter",
      /** The scope, under the field (UX-DR49). */
      help: "Gjelder alle studentene i Klasseøkten. Tiden starter når studenten åpner testen, og kan ikke stoppes. Studenter med tilrettelegging får mer tid. Testfristen gjelder fortsatt.",
      /** «Fra 15 til 240 minutter.» */
      range: (min: number, max: number) => `Fra ${min} til ${max} minutter.`,
      /** On leaving the field or saving, and the api's `out_of_range`. */
      error: (min: number, max: number) => `Skriv et helt antall minutter fra ${min} til ${max}.`,
      /** Read-only (from the Start date, or for an Assistant lecturer). */
      readOnly: (minutes: number) => `Én økt med tidsgrense: ${minutes} minutter.`,
      readOnlyOff: "Ingen tidsgrense. Testen er åpen fram til testfristen.",
      locked: "Låst fra startdatoen.",
    },
    /** Story 11.1 (FR-52, FR-53, UX-DR49): the Klasseøkt's block «Spørsmål og vekter». The title,
     * «Ta ut», «Vekt», the sum line and the quantity warning are the spine's; the rest is
     * [ASSUMPTION] draft copy for the founder's review. */
    questionSet: {
      heading: "Spørsmål og vekter",
      help: "Vektene gjelder alle studentene i Klasseøkten. Et spørsmål du tar ut, kommer ikke med i Individuell test. Spørsmål og vekter låses ved startdatoen.",
      /** A draft set (issue #16). */
      draft: "Spørsmålene er et utkast og ikke godkjent. De byttes ut før kurset tar dem i bruk.",
      /** The vekter saved on an older version of the questions no longer apply. */
      outdated: "Spørsmålene er endret siden vektene ble lagret. Vektene er satt tilbake til standard.",
      types: {
        choice: "Flervalg",
        table: "Tabell",
        number: "Tall",
        long: "Langsvar",
        /** [ASSUMPTION] Story 11.14. */
        drawn: "Graf",
      } as Record<string, string>,
      startingTask: "Fra Startoppgaven",
      quantity: "Måler mengder",
      weight: "Vekt i %",
      /** Read-only weight, «Vekt 10 %». */
      weightText: (n: number) => `Vekt ${n} %`,
      takeOut: "Ta ut",
      putBack: "Ta med igjen",
      takenOut: "Tatt ut",
      adaptedTitle: "Tilpassede oppgaver",
      adaptedHelp: "Lages fra hver students eget spill og Replay. Samme samlede vekt for alle studentene.",
      /** [ASSUMPTION] Story 11.9: the Lenke to the Adapted item preview. */
      adaptedPreview: "Se de tilpassede oppgavene med demodata",
      replacements: (n: number) =>
        `Studenter med færre enn 10 egne ordrer får ${n} vanlige oppgaver med samme samlede vekt i stedet.`,
      /** The live sum; «Sum 95 %. Vektene må bli 100 %.» blocks the save. */
      sum: (n: number) => (n === 100 ? "Sum 100 %." : `Sum ${n} %. Vektene må bli 100 %.`),
      quantityWarning: "Du tar ut en oppgave som måler mengder.",
      invalidWeight: "Skriv et helt tall fra 0 til 100.",
      save: "Lagre vekter",
      saving: "Lagrer …",
      saved: "Vektene er lagret.",
      /** Read-only reasons. */
      assistant: "Bare Faglærerne i Klassen kan endre spørsmål og vekter.",
      closed: "Startdatoen er passert. Spørsmål og vekter er låst.",
      /** Refusals beside «Lagre vekter». */
      notHundred: "Vektene må bli 100 %. Ingenting ble lagret.",
      archived: "Klassen er arkivert, så spørsmål og vekter kan ikke endres.",
      failed: "Vektene ble ikke lagret. Prøv igjen.",
      loadFailed: "Spørsmål og vekter kunne ikke hentes.",
    },
    /** Story 11.9 (FR-53, UX-DR70): the Adapted item preview, each template filled for a sample
     * Student and labelled «Demodata». The draft notice is «Spørsmål og vekter»'s own; the rest
     * is [ASSUMPTION] draft copy for the founder's review. */
    adaptedPreview: {
      title: "Tilpassede oppgaver",
      crumb: "Tilpassede oppgaver",
      lead: "Slik ser de tilpassede oppgavene ut for én student. Alle studentene får de samme oppgavene, fylt med tall fra sitt eget Klassespill og sin egen Replay.",
      /** Under the lead: where the numbers come from. */
      sample: "Tallene her er fra ett eksempelspill, ikke fra noen av studentene dine. Oppgaven fra Replay bruker tall fra det samme spillet.",
      /** The Debrief's AI-text switch may let an AI choose another approved wording (Story 11.8). */
      wordings: "Når KI-tekst er slått på, kan en KI velge en annen godkjent ordlyd for en student. Tallene er de samme.",
      /** The Adapted total weight in force, from «Spørsmål og vekter». */
      total: (n: number) => `Samlet vekt ${n} %`,
      item: (n: number) => `Oppgave ${n}`,
      sources: {
        game: "Fra Klassespillet",
        replay: "Fra Replay",
      } as Record<string, string>,
      weightText: (n: number) => `Vekt ${n} %`,
      /** A template the sample game has no fact for. */
      noFact: "Eksempelspillet har ingen slik hendelse, så denne oppgaven kan ikke vises her.",
      loadFailed: "De tilpassede oppgavene kunne ikke hentes.",
    },
    /** Story 11.2 (FR-81, UX-DR49): the Klasseøkt's block «Sensorveiledning». The title, «Standard»,
     * «Endret» and «Ikke kontrollert med en Kontrolltest.» are the spine's; the rest is [ASSUMPTION]
     * draft copy for the founder's review. */
    scoringGuide: {
      heading: "Sensorveiledning",
      help: "Sensorveiledningen sier hva KI-vurderingen ser etter i hvert langsvar og hver tilpassede oppgave. Du kan endre teksten for denne Klasseøkten. Kriteriene og skalaen er faste.",
      /** A draft guide (issue #16). */
      draft: "Sensorveiledningen er et utkast og ikke godkjent. Den byttes ut før kurset tar den i bruk.",
      /** Every version no Control test has checked, the default included (AD-27). */
      unchecked: "Ikke kontrollert med en Kontrolltest.",
      /** A newer default was published after this Klasseøkt's guide was edited. */
      outdated: "Standardveiledningen er oppdatert etter at dere endret denne. Endringene deres gjelder fortsatt.",
      /** The one five-step scale, shared by every question. */
      scaleHeading: "Skala for alle spørsmål",
      kinds: {
        long: "Langsvar",
        adapted: "Tilpasset oppgave",
      } as Record<string, string>,
      standard: "Standard",
      changed: "Endret",
      /** The Tekstfelt's label, above it. */
      guideLabel: "Veiledning",
      guideHint: "Hva oppgaven spør etter, og hvordan sterke og svake svar ser ut.",
      /** The read-only criteria under the Tekstfelt. */
      criteriaCaption: "Kriterier",
      code: "Kode",
      criterion: "Kriterium",
      weight: "Vekt",
      weightText: (n: number) => `${n} %`,
      emptyGuide: "Skriv en veiledning.",
      tooLong: (max: number) => `Skriv høyst ${max} tegn.`,
      save: "Lagre sensorveiledning",
      saving: "Lagrer …",
      saved: "Sensorveiledningen er lagret.",
      /** Read-only reasons. */
      assistant: "Bare Faglærerne i Klassen kan endre sensorveiledningen.",
      closed: "Testfristen er passert. Sensorveiledningen er låst.",
      /** Refusals beside «Lagre sensorveiledning». */
      archived: "Klassen er arkivert, så sensorveiledningen kan ikke endres.",
      invalid: "En veiledning er tom eller for lang. Ingenting ble lagret.",
      failed: "Sensorveiledningen ble ikke lagret. Prøv igjen.",
      loadFailed: "Sensorveiledningen kunne ikke hentes.",
    },
  },

  assessment: {
    /** Story 12.1 (FR-61, UX-DR49): the block «KI-vurdering» on the Klasseøkt. The title and the
     * help text are the spine's; the rest is [ASSUMPTION] draft copy for the founder's review. */
    switchBlock: {
      title: "KI-vurdering",
      /** The Bryter's state words. */
      on: "På",
      off: "Av",
      /** What the switch decides, above it. [ASSUMPTION] */
      lead: "Når KI-vurdering er på, vurderer en KI hvert langsvar i Individuell test etter testfristen. Vurderingen teller ikke og er ingen karakter.",
      help: "Flervalg og interaktive oppgaver rettes fortsatt automatisk. Studentrapporten finnes som vanlig.",
      /** Under the switch while it can change. [ASSUMPTION] */
      open: "Kan endres fram til testfristen. Da låses valget.",
      /** Pinned by the Test-deadline lock; `when` as «ti. 24. nov. kl. 10:00». [ASSUMPTION] */
      pinned: (when: string) => `Låst ved testfristen ${when}.`,
      /** The Test deadline has passed and the lock has not run yet (each minute). [ASSUMPTION] */
      deadlinePassed: "Testfristen er passert. Valget kan ikke endres.",
      /** The save refused (`ai_assessment_pinned`). [ASSUMPTION] */
      refused: "KI-vurdering kan ikke endres etter testfristen. Valget er låst.",
    },
  },

  /** The Oversikt of a Class session (Story 7.1, FR-39, UX-DR40). The headline form, «Oppdatert»,
   * the group names «Venter», «Pågår» and «Ferdig, lavest kjedekost øverst», «KI-spiller» and
   * «Spill n» are the spine's; everything else is [ASSUMPTION] draft copy for the founder's
   * review. Never a Week total or anything that hints at the game's length (FR-14). */
  overview: {
    title: "Oversikt",
    crumb: "Oversikt",
    /** The Lenke on the Klasseøkt. */
    open: "Oversikt",
    /** «Start spill» (Story 8.10, FR-22, UX-DR52, EXPERIENCE.md → Spillstyring → Start): the header
     * Lenke, the page and the result line on the Oversikt are the spine's; the empty line, the
     * refusals and the failure are [ASSUMPTION] draft copy. */
    start: {
      /** «Start spill som ikke har startet (12)», not shown with 0. */
      link: (n: number) => `Start spill som ikke har startet (${n})`,
      title: "Start spill",
      crumb: "Start spill",
      consequence: "Spillene starter for alle i dem. Reglene for ventetid gjelder fra nå.",
      /** The primary: «Start 12 spill». */
      confirm: (n: number) => `Start ${n} spill`,
      /** [ASSUMPTION] */
      listLabel: "Spill som ikke har startet",
      /** [ASSUMPTION] */
      empty: "Ingen spill venter på start.",
      /** On the Oversikt after the press: «12 spill er startet.» */
      done: (n: number) => `${n} spill er startet.`,
      /** [ASSUMPTION] */
      failed: "Spillene ble ikke startet. Prøv igjen.",
    },
    /** «Sett inn KI-spillere» (Story 8.12, FR-37, UX-DR52, EXPERIENCE.md → Spillstyring → Fill
     * waited-for Seats): the header Lenke, the page's lines, its primary and the result line on the
     * Oversikt are the spine's; the list's label, the empty line and the failure are [ASSUMPTION]
     * draft copy. */
    fill: {
      /** «Sett inn KI-spiller i alle seter som blir ventet på (9)», not shown with 0. */
      link: (n: number) => `Sett inn KI-spiller i alle seter som blir ventet på (${n})`,
      title: "Sett inn KI-spillere",
      crumb: "Sett inn KI-spillere",
      /** One waited-for Seat under its game: «Noah, 23 t». */
      seat: (name: string, wait: string) => `${name}, ${wait}`,
      consequence: "Studentene kan ta setene tilbake fra neste Uke.",
      /** The primary: «Sett inn 9 KI-spillere». */
      confirm: (n: number) => (n === 1 ? "Sett inn 1 KI-spiller" : `Sett inn ${n} KI-spillere`),
      /** [ASSUMPTION] */
      listLabel: "Seter som blir ventet på",
      /** [ASSUMPTION] */
      empty: "Ingen seter blir ventet på nå.",
      /** On the Oversikt after the press: «9 KI-spillere er satt inn.» */
      done: (n: number) => (n === 1 ? "1 KI-spiller er satt inn." : `${n} KI-spillere er satt inn.`),
      /** [ASSUMPTION] */
      failed: "KI-spillerne ble ikke satt inn. Prøv igjen.",
    },
    /** «Klasseøkt 2, class-of-1994» beside the heading. */
    session: (number: number, className: string) => `Klasseøkt ${number}, ${className}`,
    counts: {
      finished: (n: number) => `${n} ferdig`,
      running: (n: number) => `${n} pågår`,
      /** Story 8.6: «15 pågår (herav 2 pauset)», EXPERIENCE.md → Oversikt Live. */
      runningPaused: (n: number, paused: number) => `${n} pågår (herav ${paused} pauset)`,
      waiting: (n: number) => `${n} venter`,
      /** [ASSUMPTION] Class games that have not started after the Start date. */
      notStarted: (n: number) => `${n} ikke startet`,
    },
    updated: (clock: string) => `Oppdatert ${clock}`,
    groups: {
      waiting: "Venter",
      /** Story 8.6: between Venter and Pågår (EXPERIENCE.md → Oversikt → Grouping). */
      paused: "Pause",
      running: "Pågår",
      /** [ASSUMPTION] */
      notStarted: "Ikke startet",
      finished: "Ferdig, lavest kjedekost øverst",
    },
    /** «Pause siden ma. 14:10, satt av Sara.» (Story 8.6, EXPERIENCE.md → Spillinnsikt Paused, the
     * Oversikt's «since when and by whom»): [ASSUMPTION] copy. Never a Week count. */
    pausedSince: (since: string, name: string | null) =>
      name ? `Pause siden ${since}, satt av ${name}.` : `Pause siden ${since}.`,
    game: (number: number | null) => gameName(number),
    /** The wall's and the table's row label of a game marked «I rommet» (Story 8.11, FR-36,
     * EXPERIENCE.md → Spillstyring → I rommet): «Spill 3 · I rommet». */
    gameInRoom: (number: number | null) => `${gameName(number)} · I rommet`,
    week: (week: number) => `Uke ${week}`,
    /** «Venter på Noah (Grossist), 23 t». [ASSUMPTION] */
    waitingFor: (who: string, role: string, duration: string) => `Venter på ${who} (${role}), ${duration}`,
    /** A waited-for Student no longer in the Class: by Role only. [ASSUMPTION] */
    waitingForRole: (role: string, duration: string) => `Venter på ${role}, ${duration}`,
    /** [ASSUMPTION] the wall row's note where the full one has no room (Story 7.6): «Venter, 23 t». */
    waitingShort: (duration: string) => `Venter, ${duration}`,
    seat: (role: string, holder: string) => `${role}: ${holder}`,
    /** [ASSUMPTION] Story 8.3: an AI-held Seat with its AD-15 mark in the game list, «Fabrikk:
     * KI-spiller (KI tok over etter ventetiden)», and in the wall row's note, «Fabrikk: KI tok over
     * etter ventetiden». */
    seatMarked: (role: string, holder: string, mark: string) => `${role}: ${holder} (${mark})`,
    seatMark: (role: string, mark: string) => `${role}: ${mark}`,
    aiPlayer: "KI-spiller",
    /** [ASSUMPTION] a free Seat, before the lock gives it an AI player. */
    freeSeat: "Ledig",
    /** [ASSUMPTION] a Student no longer in the Class. */
    unknownStudent: "Student",
    chainCost: "Kjedekost",
    seatsLabel: (game: string) => `Seter i ${game}`,
    /** Before the Start date (Story 7.1). [ASSUMPTION] */
    beforeStart: {
      title: "Fordeling",
      startsAt: (date: string) => `Spillene starter ${date}. Til da vises bare fordelingen.`,
      noDate: "Spillene starter på startdatoen. Til da vises bare fordelingen.",
      empty: "Ingen spill er fordelt ennå.",
    },
    /** [ASSUMPTION] after the Start date with no Class game at all. */
    empty: "Klasseøkten har ingen klassespill.",
    /** [ASSUMPTION] Story 7.2: the heading of the game list under the Matrisevegg. */
    listTitle: "Spill og seter",
    /** The Varselbånd (Stories 7.11 and 8.3, UX-DR45): «Spill 2 venter på Noah (Grossist) i 23 t.
     * KI overtar om 1 t.» is the spine's; the rest is [ASSUMPTION]. Stories 8.5–8.7 add its other
     * actions. */
    band: {
      /** [ASSUMPTION] the band's accessible name: the game an AI player takes over first. */
      label: "Spillet nærmest at KI tar over",
      /** The countdown after the wait, from the api's due time (Story 8.3): «KI overtar om 1 t.» */
      takeover: (duration: string) => `KI overtar om ${duration}.`,
      /** [ASSUMPTION] the due time has passed and the sweep acts within the minute. */
      takeoverNow: "KI overtar nå.",
      text: (game: string, name: string | null, role: string, duration: string) =>
        name ? `${game} venter på ${name} (${role}) i ${duration}.` : `${game} venter på ${role} i ${duration}.`,
      /** [ASSUMPTION] read out when the band appears or changes game: the line without its duration. */
      said: (game: string, name: string | null, role: string) =>
        name ? `${game} venter på ${name} (${role}).` : `${game} venter på ${role}.`,
    },
    /** «Oppdater automatisk» and the Oversikt's Tilkoblingslinje (Story 7.5, EXPERIENCE.md →
     * Oppdater automatisk and State Patterns → Oversikt). */
    live: {
      label: "Oppdater automatisk",
      /** [ASSUMPTION] the Bryter's state words. */
      on: "På",
      off: "Av",
      /** «3 endringer siden 14:02»; [ASSUMPTION] the singular «1 endring». */
      changes: (n: number, clock: string) => `${n} ${n === 1 ? "endring" : "endringer"} siden ${clock}`,
      apply: "Oppdater",
      stale: (clock: string) => `Ikke oppdatert siden ${clock}. Prøver igjen.`,
      reload: "Last inn på nytt",
      /** [ASSUMPTION] a background read failed while the stream is live. */
      failed: (clock: string) => `Ikke oppdatert siden ${clock}.`,
    },
    /** The right rail (Story 7.6, UX-DR40, UX-DR51, UX-DR69, UX-DR72, `08-laerer-oversikt.png`).
     * The headings, «Snitt per ferdig spill, per Rolle», the AI line and the Trakt's stage names
     * are the mockup's and the epic's; the rest is [ASSUMPTION]. */
    rail: {
      label: "Klassen samlet",
      waiting: {
        title: "Venter ellers",
        /** [ASSUMPTION] */
        none: "Ingen spill venter nå.",
        /** [ASSUMPTION] the band's game waits, no other does (Story 7.11). */
        noneOther: "Ingen andre spill venter.",
        /** «Ida, Detaljist, 18 t». */
        who: (name: string, role: string, duration: string) => `${name}, ${role}, ${duration}`,
        whoRole: (role: string, duration: string) => `${role}, ${duration}`,
        /** A Pause with an agreed time (Story 8.7, Epic 8 close-out): «Pause i Uke 29, fortsetter
         * to. 19:00». [ASSUMPTION] the line without a Week. */
        pausedUntil: (week: number | null, when: string) =>
          week == null ? `Pause, fortsetter ${when}` : `Pause i Uke ${week}, fortsetter ${when}`,
        /** «22 KI-spillere i 17 spill, alle merket.»; [ASSUMPTION] the singular and none. */
        ai: (seats: number, games: number) =>
          seats === 0
            ? "Ingen KI-spillere."
            : seats === 1
              ? `1 KI-spiller i 1 spill, merket.`
              : `${seats} KI-spillere i ${games} spill, alle merket.`,
      },
      cost: {
        title: "Klassens kostnad",
        /** «Kjedekost i 41 ferdige spill. Hvert merke er ett spill.» */
        intro: (games: number) => `Kjedekost i ${games} ${games === 1 ? "ferdig spill" : "ferdige spill"}. Hvert merke er ett spill.`,
        /** [ASSUMPTION] */
        none: "Ingen spill er ferdige ennå.",
        median: (value: string) => `Median ${value}`,
        axis: "Kroner. Boksen er midterste halvdel.",
        /** «Median 1 954. Midterste halvdel 1 500–2 600.» (EXPERIENCE.md → Charts). */
        summary: (median: string, low: string, high: string) => `Median ${median}. Midterste halvdel ${low}–${high}.`,
        /** [ASSUMPTION] the SVG title. */
        chartTitle: (games: number) => `Kjedekost i hvert ferdige spill, ${games} spill`,
        showTable: "Vis som tabell",
        showChart: "Vis som graf",
        /** [ASSUMPTION] */
        tableCaption: "Kjedekost per ferdige spill, lavest først",
        gameColumn: "Spill",
        costColumn: "Kjedekost, kr",
        rolesTitle: "Snitt per ferdig spill, per Rolle",
        /** [ASSUMPTION] read with the printed amount: «Detaljist: lager 120, restordre 93, i alt 213 kr». */
        roleName: (role: string, holding: string, backorder: string, total: string) =>
          `${role}: lager ${holding}, restordre ${backorder}, i alt ${total} kr`,
        /** The key: «lager 949», «restordre 1 063 kr». */
        keyHolding: (amount: string) => `lager ${amount}`,
        keyBackorder: (amount: string) => `restordre ${amount} kr`,
      },
      funnel: {
        title: "Trakt",
        stages: {
          registered: "Registrert",
          class_game: "Klassespill ferdig",
          debrief: "Debrief ferdig",
          quiz_passed: "Quiz bestått",
          replay: "Replay ferdig",
          test_submitted: "Test levert",
          assessment_ready: "KI-vurdering klar",
        },
      },
    },
  },

  /** The Matrisevegg (Story 7.2, DESIGN.md → Components → Matrisevegg, EXPERIENCE.md →
   * Matrisevegg). The legend's bins and its minus line are DESIGN.md's own. */
  wall: {
    region: "Alle spill",
    /** [ASSUMPTION] the SVG title: «Netto lager for Fabrikk per uke i alle spill». */
    title: (measure: string, role: string) => `${measure} for ${role} per uke i alle spill`,
    /** [ASSUMPTION] the Landing's SVG title: no Role named beside the one-Seat figure. */
    demoTitle: "Netto lager per uke i hvert spill, demodata",
    gameHeader: "Spill",
    /** [ASSUMPTION] the header over the kjedekost figures, in whole kroner. */
    figureHeader: "Kjedekost, kr",
    /** [ASSUMPTION] the line above the wall naming what its cells show: «Netto lager, Fabrikk». */
    shown: (measure: string, role: string) => `${measure}, ${role}`,
    week: (week: number) => `Uke ${week}`,
    /** «Spill 2, Uke 14: Netto lager −13.» [ASSUMPTION: copy of the cell reading] */
    cell: (game: string, week: number, measure: string, value: string) => `${game}, Uke ${week}: ${measure} ${value}.`,
    legend: "Fargeskala for netto lager",
    bins: [
      "−35 og lavere",
      "−34 til −20",
      "−19 til −10",
      "−9 til −1",
      "0",
      "1 til 9",
      "10 til 19",
      "20 til 34",
      "35 og over",
    ],
    minusNote: "− i en celle: restordre (under null).",
    /** [ASSUMPTION] the legend for Ordre and Kost per uke (Story 7.4): DESIGN.md's flow bins,
     * «<5 no fill; 5–9 / 10–19 / 20–29 / 30+», in words. */
    flowLegend: (measure: string) => `Fargeskala for ${measure.toLowerCase()}`,
    flowBins: ["Under 5", "5 til 9", "10 til 19", "20 til 29", "30 og over"],
    /** Veggfiltre (Story 7.4, UX-DR43). «Rolle», «Celler», «Status», «Alle» and «Med KI-spiller»
     * are the mockup's (`08-laerer-oversikt.png`). */
    filters: {
      role: "Rolle",
      cells: "Celler",
      status: "Status",
      all: "Alle",
      withAi: "Med KI-spiller",
      /** [ASSUMPTION] in place of the wall when the Status filter matches no game. */
      empty: "Ingen spill i dette utvalget.",
    },
    /** The class median graph and the rows under the wall (Story 7.4, UX-DR40, UX-DR41).
     * «Median, Fabrikk» and «Kjedekost/uke, snitt» are DESIGN.md's own. */
    median: {
      /** [ASSUMPTION] the graph's key above the wall. */
      line: "Median",
      band: "Midterste halvdel av spillene",
      row: (role: string) => `Median, ${role}`,
      chainRow: "Kjedekost/uke, snitt",
      /** [ASSUMPTION] a median cell as read. */
      cell: (week: number, median: string, low: string, high: string, games: number) =>
        `Uke ${week}: median ${median}, midterste halvdel ${low} til ${high}, ${games} spill.`,
      /** [ASSUMPTION] a mean chain cost cell as read. */
      chainCell: (week: number, value: string) => `Uke ${week}: kjedekost per uke, snitt ${value} kr.`,
      /** [ASSUMPTION] shown when the median rows cannot be read; the wall stays. */
      failed: "Medianen kunne ikke hentes.",
    },
    /** Status words after the cells and in the row header. [ASSUMPTION] */
    status: {
      waiting: "Venter",
      running: "Pågår",
      /** Story 8.6: a paused Class game. */
      paused: "Pause",
      notStarted: "Ikke startet",
      finished: "Ferdig",
    },
    /** The row header as read: «Spill 2, venter på Noah (Grossist), 23 t, kjedekost 1 058 kr».
     * [ASSUMPTION] */
    rowName: (parts: readonly string[]) => parts.join(", "),
    chainCost: (cost: string) => `kjedekost ${cost}`,
    /** The Visningsbryter and «Vis som tabell» (Story 7.3, UX-DR42). «Vegg» and «Vis som tabell»
     * are EXPERIENCE.md's own; «Visning» is the mockup's (`08-laerer-oversikt.png`). */
    table: {
      view: "Visning",
      wall: "Vegg",
      table: "Vis som tabell",
      /** [ASSUMPTION] the column headers beside «Spill» and «Kjedekost, kr». */
      status: "Status",
      waitingFor: "Venter på",
      /** «Noah (Grossist), 23 t»; a Student no longer in the Class is named by Role. [ASSUMPTION] */
      wait: (who: string, role: string, duration: string) => `${who} (${role}), ${duration}`,
      waitRole: (role: string, duration: string) => `${role}, ${duration}`,
      /** [ASSUMPTION] the read-only header of the «Melding» column (Story 7.11). */
      link: "Melding",
    },
  },

  /** Spillinnsikt (Story 7.7, FR-62, FR-34, UX-DR55): one Class game week by week for the staff.
   * «Spillet har ikke startet.» and «KI-spiller» are the spine's; the rest is [ASSUMPTION] draft
   * copy for the founder's review. The page never shows a Week total. */
  insight: {
    crumb: (game: string) => game,
    /** «Spill 2» as the page heading and tab title. */
    title: (number: number | null) => gameName(number),
    /** Story 10.5 (FR-34): a Student's Replay on Spillinnsikt, labelled as one. [ASSUMPTION] */
    replayTitle: "Replay",
    status: {
      waiting: "Venter",
      running: "Pågår",
      /** Story 8.6: a paused Class game. */
      paused: "Pause",
      not_started: "Ikke startet",
      finished: "Ferdig",
    },
    /** Story 10.6: a Replay closed at the Testfrist unfinished, in place of «Ferdig». [ASSUMPTION] */
    closedAtTestDeadline: "Stengt ved Testfristen, ikke fullført",
    /** Read before the status word. */
    statusLabel: "Status",
    seatsTitle: "Setene",
    /** The Seats' list name. */
    seatsLabel: "Setene i kjeden, Fabrikk først",
    aiPlayer: "KI-spiller",
    freeSeat: "Ledig",
    unknownStudent: "Student",
    /** The link slot of a Student Seat while no Explanation or Debrief summary exists (Epic 9
     * fills it). [ASSUMPTION] */
    noLinks: "Forklaring og Debrief-sammendrag kommer når studenten har kommet dit.",
    /** The words of each link kind a later epic registers. [ASSUMPTION] */
    links: {
      explanation: "Forklaring",
      debrief_summary: "Debrief-sammendrag",
      /** Story 10.5: the Student's Replay, from their Seat on the Class game. */
      replay: "Replay",
    } as Record<string, string>,
    /** A link kind with no words of its own yet. [ASSUMPTION] */
    otherLink: "Åpne",
    notStarted: "Spillet har ikke startet.",
    /** The charts over the per-Role tables (Story 7.8, FR-62, UX-DR33, UX-DR55). [ASSUMPTION] but
     * «Vis som tabell», «Ordrestolper» and «Kundene», which are the spine's. */
    charts: {
      title: "Kjeden i grafer",
      week: "Uke",
      weekLabel: (week: number) => `Uke ${week}`,
      showTable: "Vis som tabell",
      showChart: "Vis som graf",
      swipe: "Sveip for tidligere uker",
      axisSvg: "Rollene, Fabrikk øverst",
      orders: {
        title: "Ordre",
        key: "Ordre per uke, Fabrikk øverst og kundenes etterspørsel nederst. Prikken med «Uke n» viser hver rolles første ordre på 10 eller mer.",
        region: "Ordrestolper og ordre per rolle og uke",
        tableRegion: "Ordre per rolle og uke",
        svg: "Ordrestolper: ordre per rolle og uke",
        customers: "Kundene",
        /** OrderBarsTable's texts for a column Spillinnsikt does not show yet (Forsterkning comes
         * with Story 9.5) and a viewer's own Role, which staff have none of. */
        amplification: "Forsterkning",
        own: "(deg)",
        none: "–",
      },
      stock: {
        title: "Lager og restordre",
        key: "Lager over streken, restordre under. Samme skala for alle rollene.",
        region: "Lager og restordre per rolle og uke",
        tableRegion: "Lager og restordre per rolle og uke, tabell",
        svg: "Lager og restordre per rolle og uke",
        stockRow: (role: string) => `${role}, lager`,
        backlogRow: (role: string) => `${role}, restordre`,
      },
    },
    /** The heading over the per-Role tables. */
    weeksTitle: "Uke for uke",
    /** The region of one Role's table, «Detaljist uke for uke». */
    region: (role: string) => `${role} uke for uke`,
    columns: {
      week: "Uke",
      playedBy: "Spilt av",
      incomingOrder: "Ordre inn",
      incomingDelivery: "Levering inn",
      inventory: "Lager",
      backlog: "Restordre",
      order: "Ordre",
      cost: "Kost, kr",
      /** When the Week opened for the Seat, when its Order came and the time between (Story 8.1,
       * FR-35). [ASSUMPTION] */
      opened: "Uke åpnet",
      ordered: "Bestilt",
      took: "Tid brukt",
      marks: "Merknad",
    },
    /** «18. nov. kl. 13:01», Europe/Oslo: when a Week opened or an Order came. [ASSUMPTION] */
    at: (date: string, time: string) => `${date} kl. ${time}`,
    /** An Order not placed yet in the open Week, as read. */
    noOrder: "ikke lagt inn",
    /** The marks of the one AD-15 mapping, always in text (FR-34). */
    marks: {
      guard_switch: "Byttet til regelbasert KI (spillvakt)",
      cost_limit: "Byttet til regelbasert KI (kostnadsgrense)",
      takeover_inactivity: "KI tok over etter ventetiden",
      takeover_staff: "KI satt inn av faglærer",
      takeover_peer: "KI satt inn av gruppa",
      reclaim: "Studenten tok setet tilbake",
      playout: "KI spilte spillet ferdig",
      fallback_timeout: "Reserveordre: KI svarte ikke i tide",
      fallback_invalid_output: "Reserveordre: KI ga ugyldig svar",
      fallback_budget_exhausted: "Reserveordre: KI-budsjettet var brukt opp",
      fallback_provider_error: "Reserveordre: feil hos KI-tjenesten",
    },
    /** A Takeover by a person, named at read time (Story 8.5, FR-37): «KI satt inn av Bård».
     * [ASSUMPTION] */
    markedBy: (name: string) => `KI satt inn av ${name}`,
  },

  /** Spillstyring on Spillinnsikt, and the Varselbånd's Takeover (Story 8.5, FR-37, UX-DR45,
   * UX-DR52, EXPERIENCE.md → Spillstyring). */
  spillstyring: {
    title: "Spillstyring",
    /** The secondary per-Seat button: «Sett inn KI-spiller for Jonas». */
    takeover: (name: string) => `Sett inn KI-spiller for ${name}`,
    /** The consequence directly above the button: the Student has not ordered this Uke… */
    thisWeek: (name: string) =>
      `KI-spilleren bestiller for ${name} fra denne Uka. ${name} kan ta setet tilbake fra neste Uke.`,
    /** …or has. */
    nextWeek: (name: string) => `KI-spilleren bestiller for ${name} fra neste Uke.`,
    /** The result line that replaces the button and takes focus. */
    done: (name: string) => `KI-spiller satt inn for ${name}.`,
    /** A Seat row's name: «Fabrikk: Jonas». [ASSUMPTION] */
    seat: (role: string, name: string) => `${role}: ${name}`,
    /** A Seat with Tilrettelegging, for the Lecturer only (Story 8.9, UX-DR52, EXPERIENCE.md →
     * Spillstyring → Manual Takeover): «Jonas har tilrettelegging med mer tid.» */
    extraTime: (name: string) => `${name} har tilrettelegging med mer tid.`,
    /** Who acted first, from the view read again (`takeover_exists`, EXPERIENCE.md → AI put in by
     * two at once): «Sara har allerede satt inn en KI-spiller.» */
    taken: (name: string) => `${name} har allerede satt inn en KI-spiller.`,
    /** [ASSUMPTION] the automatic Takeover came first. */
    takenBySystem: "KI-spilleren har allerede tatt over setet etter ventetiden.",
    /** [ASSUMPTION] someone no longer named in the Class came first. */
    takenByUnknown: "En KI-spiller er allerede satt inn.",
    /** The other refusals. [ASSUMPTION] */
    refusals: {
      seat_not_student_held: "Ingen student har dette setet nå.",
      game_not_running: "Spillet er ikke i gang.",
      takeover_not_allowed: "KI-spiller kan ikke settes inn i dette spillet.",
      /** The Student has ordered the game's last Uke: no Uke is left for a KI-spiller. */
      order_exists: "Studenten har bestilt, og det er ingen neste Uke.",
      play_deadline_passed: "Spillfristen er nådd, og KI-spillere har tatt over spillet.",
    } as Record<string, string>,
    /** [ASSUMPTION] */
    failed: "KI-spilleren ble ikke satt inn. Prøv igjen.",
    /** «Start spillet» (Story 8.10, FR-22, UX-DR52, EXPERIENCE.md → Spillstyring → Start): the
     * button, its consequence and «Spillet er startet.» are the spine's; who started it first and
     * the refusals are [ASSUMPTION] draft copy. */
    start: {
      consequence: "Spillet starter for alle fire. Reglene for ventetid gjelder fra nå.",
      button: "Start spillet",
      done: "Spillet er startet.",
      /** Someone started it first, named from the view read again: «Spillet ble startet av Sara.» */
      startedBy: (name: string) => `Spillet ble startet av ${name}.`,
      /** …by no one the Class still names. */
      startedAlready: "Spillet er allerede startet.",
      refusals: {
        game_not_ready: "Spillet kan ikke startes før Startdatoen.",
      } as Record<string, string>,
      failed: "Spillet ble ikke startet. Prøv igjen.",
    },
    /** «Sett inn KI-spiller i alle seter som blir ventet på (2)» on one game (Story 8.12, FR-37,
     * UX-DR52): the button, «Ikke med (tilrettelegging): Jonas» and «2 KI-spillere satt inn.» are
     * the spine's; the consequence line (EXPERIENCE.md has none, open-assumptions.md), the line
     * when none was put in and the failure are [ASSUMPTION] draft copy. */
    fill: {
      button: (n: number) => `Sett inn KI-spiller i alle seter som blir ventet på (${n})`,
      /** [ASSUMPTION] «KI-spillere bestiller for Noah og Emma fra denne Uka. Studentene kan ta
       * setene tilbake fra neste Uke.» */
      consequence: (names: string) =>
        `KI-spillere bestiller for ${names} fra denne Uka. Studentene kan ta setene tilbake fra neste Uke.`,
      /** The Seats left out: «Ikke med (tilrettelegging): Jonas». */
      leftOut: (names: string) => `Ikke med (tilrettelegging): ${names}`,
      /** The result line that replaces the button and takes focus: «2 KI-spillere satt inn.» */
      done: (n: number) => (n === 1 ? "1 KI-spiller satt inn." : `${n} KI-spillere satt inn.`),
      /** [ASSUMPTION] every Seat had ordered or been taken meanwhile. */
      none: "Ingen KI-spillere satt inn. Setene blir ikke ventet på lenger.",
      /** [ASSUMPTION] */
      failed: "KI-spillerne ble ikke satt inn. Prøv igjen.",
    },
    /** The Lecturer's Pause (Story 8.7, FR-89, UX-DR52, EXPERIENCE.md → Spillstyring → Pause). */
    pause: {
      open: "Pause spillet",
      change: "Endre avtalt tid",
      end: "Avslutt pausen",
      title: "Når fortsetter spillet?",
      date: "Dato",
      time: "Klokkeslett",
      noTime: "Uten avtalt tid",
      noTakeover: "Mens spillet har pause, tar ingen KI-spiller over setene. Spillfristen flyttes ikke.",
      afterTime: "Etter avtalt tid kan studentene sette inn en KI-spiller for den som ikke har bestilt.",
      /** The primary: «Ta pause til to. 19:00», «Ta pause uten avtalt tid», or «Ta pause til …»
       * while no time is chosen yet: it names that a time comes (Epic 8 close-out, from the 8.7
       * visual check). [ASSUMPTION] */
      confirmAt: (when: string) => `Ta pause til ${when}`,
      confirmNoTime: "Ta pause uten avtalt tid",
      confirm: "Ta pause til …",
      /** «Endre avtalt tid»'s primary. [ASSUMPTION] */
      saveAt: (when: string) => `Lagre avtalt tid ${when}`,
      saveNoTime: "Lagre uten avtalt tid",
      save: "Lagre avtalt tid",
      cancel: "Avbryt",
      /** Spillinnsikt → Paused: «Pause siden ma. 14:10, satt av Sara.» or «… satt av deg.». */
      since: (since: string, name: string | null) =>
        name ? `Pause siden ${since}, satt av ${name}.` : `Pause siden ${since}.`,
      sinceMine: (since: string) => `Pause siden ${since}, satt av deg.`,
      /** [ASSUMPTION] the agreed time after the line. */
      agreed: (when: string) => `Avtalt tid ${when}.`,
      /** The result lines that replace the form and take focus. */
      doneAt: (when: string) => `Pause til ${when} er satt.`,
      /** [ASSUMPTION] */
      doneNoTime: "Spillet har pause uten avtalt tid.",
      /** [ASSUMPTION] */
      ended: "Pausen er avsluttet.",
      /** [ASSUMPTION] a time not after now, in a Class session with no Spillfrist. */
      afterNow: "Velg et tidspunkt etter nå.",
      /** [ASSUMPTION] someone paused first: the line read again says who. */
      already: "Spillet har allerede pause.",
      refusals: {
        game_finished: "Spillet er ferdig.",
        game_not_running: "Spillet er ikke i gang.",
        pause_not_allowed: "Dette spillet kan ikke settes på pause.",
        not_paused: "Spillet har ikke pause lenger.",
        play_deadline_passed: "Spillfristen er nådd, og KI-spillere har tatt over spillet.",
      } as Record<string, string>,
      /** [ASSUMPTION] */
      failed: "Det gikk ikke. Prøv igjen.",
    },
    /** «I rommet» (Story 8.11, FR-36, UX-DR52, EXPERIENCE.md → Spillstyring → I rommet): the
     * button, the form's label, line and primary, the marked line, «Ikke i rommet lenger», «I rommet
     * til 16:00.» and «Kan bare brukes i en Labtime.» are the spine's; the field's help and error,
     * the ended line, the refusals and the failure are [ASSUMPTION] draft copy. */
    inRoom: {
      open: "Marker som i rommet",
      /** Shown with the unavailable button outside every Labtime. */
      onlyInLabHour: "Kan bare brukes i en Labtime.",
      field: "Ventetid i rommet",
      /** [ASSUMPTION] the field's unit and range, under its label. */
      help: "Hele minutter, fra 2 til 120.",
      /** [ASSUMPTION] the Ordrefelt error pattern. */
      error: "Skriv et helt antall minutter fra 2 til 120.",
      consequence: (until: string) =>
        `Studentene i spillet ser den kortere ventetiden. Den gjelder til Labtimen slutter kl. ${until}.`,
      /** The primary: «Marker som i rommet, 10 min»; without a valid number, without minutes. */
      confirm: (minutes: number | null) =>
        minutes === null ? "Marker som i rommet" : `Marker som i rommet, ${minutes}\u00a0min`,
      cancel: "Avbryt",
      /** «I rommet til 16:00. KI tar over etter 10 min uten ordre.» */
      marked: (until: string, minutes: number) =>
        `I rommet til ${until}. KI tar over etter ${minutes}\u00a0min uten ordre.`,
      end: "Ikke i rommet lenger",
      /** The result line that replaces the form and takes focus: «I rommet til 16:00.» */
      done: (until: string) => `I rommet til ${until}.`,
      /** [ASSUMPTION] */
      ended: "Ikke i rommet lenger. Den vanlige ventetiden gjelder igjen.",
      refusals: {
        not_in_lab_hour: "Kan bare brukes i en Labtime.",
        already_in_room: "Spillet er allerede markert som i rommet.",
        not_in_room: "Spillet er ikke i rommet lenger.",
        game_finished: "Spillet er ferdig.",
        game_not_running: "Spillet er ikke i gang.",
        in_room_not_allowed: "Dette spillet kan ikke markeres som i rommet.",
        minutes_out_of_range: "Skriv et helt antall minutter fra 2 til 120.",
      } as Record<string, string>,
      /** [ASSUMPTION] */
      failed: "Det gikk ikke. Prøv igjen.",
    },
  },

  /** The Studentside (Story 8.9, UX-DR53, EXPERIENCE.md → Studentside and Tilrettelegging), for
   * the staff of the Class: «Tilrettelegging» and «Frister» for its Lecturers, and the record
   * blocks of Story 13.2 (FR-63) for its Lecturers and Assistant lecturers. */
  reports: {
    studentPage: {
      /** The crumb and the link from Spillinnsikt are the Student's name. */
      linkLabel: (name: string) => `Studentside for ${name}`,
      /** [ASSUMPTION] the line under the name. */
      session: (number: number) => `Klasseøkt ${number}`,
      /** [ASSUMPTION] The Roster's link from a registered Student (Story 13.2): «Studentside» for
       * a Class with one Klasseøkt, «Studentside, økt 2» for each where it has several. */
      rosterLink: "Studentside",
      rosterLinkSession: (number: number) => `Studentside, økt ${number}`,
      rosterLinkLabel: (email: string, number: number) => `Studentside for ${email}, Klasseøkt ${number}`,
    },
    /** The block «Fullføring» (Story 13.2, FR-17, UX-DR54, EXPERIENCE.md → Fullføringsretting):
     * the step names, «gjort» / «ikke gjort» and the two share lines are the spine's; the rest is
     * [ASSUMPTION] draft copy for the founder's review. */
    completion: {
      title: "Fullføring",
      steps: {
        class_game: "Klassespill",
        debrief: "Debrief",
        quiz_passed: "Debrief-quiz",
        replay: "Replay",
        test_submitted: "Individuell test",
      } as Record<string, string>,
      done: "gjort",
      notDone: "ikke gjort",
      /** «Registrert ti. 12. des.»: when the step event was recorded (the day ends in its own
       * full stop). */
      recorded: (day: string) => `Registrert ${sentence(day)}`,
      /** A recorded step that does not count, said in text. */
      notCounted: {
        class_game: "Spillet er ferdig, men studenten bestilte selv for sjelden.",
        debrief: "Debriefen er fullført, men Forklaringen er for kort.",
        test_submitted: "Testen ble levert ved fristen, men en del mangler svar.",
      } as Record<string, string>,
      /** «Bestilte i 70 % av ukene.» */
      ordered: (percent: string) => `Bestilte i ${percent} av ukene.`,
      /** Story 13.4: with an Oppfølgingsspill the share names its game: «Bestilte i 100 % av ukene
       * i Oppfølgingsspillet.» [ASSUMPTION] */
      orderedIn: (percent: string, game: "class" | "makeup") =>
        `Bestilte i ${percent} av ukene i ${game === "makeup" ? "Oppfølgingsspillet" : "Klassespillet"}.`,
      /** « Kravet er 80 %.», only when the Class session is obligatory. */
      required: (percent: string) => `Kravet er ${percent}.`,
      /** The Student's own share (Tilrettelegging): «Kravet er 60 % (tilrettelagt).» */
      requiredAdjusted: (percent: string) => `Kravet er ${percent} (tilrettelagt).`,
      /** «20 % av ukene ble spilt i utspillingen ved Spillfristen.» */
      playout: (percent: string) => `${percent} av ukene ble spilt i utspillingen ved Spillfristen.`,
      met: "Kravet er oppfylt.",
      notMet: "Kravet er ikke oppfylt.",
      unavailable: "Fullføringen telles ikke for denne studenten.",
      /** Participation signals (FR-17): never part of the status. */
      infoTitle: "Til informasjon",
      infoNote: "Endrer ikke fullføringen.",
      /** «Tid på egne bestillinger: 1 t 4 min.» */
      timeSpent: (time: string) => `Tid på egne bestillinger: ${time}.`,
      hoursMinutes: (hours: number, minutes: number) => (hours > 0 ? `${hours} t ${minutes} min` : `${minutes} min`),
      underMinute: "under 1 min",
      /** Over the Student's own Orders after the Guided Weeks only. */
      constant: (count: number) => `De ${count} egne bestillingene etter de veiledede ukene hadde samme antall.`,
      varied: (count: number) => `De ${count} egne bestillingene etter de veiledede ukene hadde ulike antall.`,
      tooFew: "For få egne bestillinger etter de veiledede ukene til å si om de var like.",
      noOrders: "Ingen egne bestillinger.",
      /** Story 13.3 (UX-DR54, EXPERIENCE.md → Fullføringsretting): the correction of a step. The
       * spine's strings; the legend, the refusals, the failure and the fallback name are
       * [ASSUMPTION]. */
      correct: (step: string) => `Rett ${step}`,
      doneChoice: "Gjort",
      notDoneChoice: "Ikke gjort",
      statusLegend: "Status",
      reasonLabel: "Begrunnelse",
      reasonError: "Skriv en begrunnelse.",
      reasonTooLong: "Begrunnelsen kan være på høyst 1000 tegn.",
      logged: "Rettingen logges med navnet ditt, tidspunktet og begrunnelsen.",
      save: "Lagre retting",
      cancel: "Avbryt",
      /** «Gjort, rettet av Bård 12. des.» (the day ends in its own full stop). */
      corrected: (done: boolean, by: string, day: string) => `${done ? "Gjort" : "Ikke gjort"}, rettet av ${by} ${sentence(day)}`,
      /** The corrector's name when it is no longer known in the Class. */
      someone: "en faglærer",
      refusals: {
        invalid_correction: "Sjekk begrunnelsen.",
        not_obligatory: "Klasseøkta er ikke obligatorisk, så det er ingenting å rette.",
        class_archived: "Klassen er arkivert, så ingenting kan rettes.",
      } as Record<string, string>,
      failed: "Rettingen ble ikke lagret. Prøv igjen.",
      /** Story 13.4 (UX-DR54, EXPERIENCE.md → Fullføringsretting → Oppfølgingsspill): the spine's
       * strings; the state lines, the refusals and the failure are [ASSUMPTION]. */
      makeup: {
        give: "Gi oppfølgingsspill",
        /** «Jonas får et eget Klassespill mot tre KI-spillere, åpent til Testfristen fr. 18. des.
         * Jonas får beskjed på Hjem og på e-post.» (the day ends in its own full stop) */
        consequence: (name: string, day: string) =>
          `${name} får et eget Klassespill mot tre KI-spillere, åpent til Testfristen ${sentence(day)} ${name} får beskjed på Hjem og på e-post.`,
        /** «Oppfølgingsspill gitt 12. des. Åpent til fr. 18. des.» */
        given: (given: string, until: string) => `Oppfølgingsspill gitt ${sentence(given)} Åpent til ${sentence(until)}`,
        /** Without a Testfrist any more (it was removed after the Oppfølgingsspill was given). */
        givenOn: (given: string) => `Oppfølgingsspill gitt ${sentence(given)}`,
        state: {
          ready: "Ikke startet ennå.",
          running: "Pågår.",
          finished: "Ferdig.",
          ended: "Stengt ved Testfristen før siste uke.",
        } as Record<string, string>,
        cancel: "Avbryt",
        refusals: {
          not_counted: "Studenten telles ikke i rapportene, så et Oppfølgingsspill teller ikke.",
          session_not_locked: "Klasseøkta er ikke låst ennå, så det finnes ikke noe spill å gi.",
          no_test_deadline: "Klasseøkta har ingen Testfrist.",
          test_deadline_passed: "Testfristen er ute.",
          class_archived: "Klassen er arkivert.",
        } as Record<string, string>,
        failed: "Oppfølgingsspillet ble ikke gitt. Prøv igjen.",
      },
    },
    /** The record blocks of the Studentside (Story 13.2, FR-63). All [ASSUMPTION] draft copy. */
    record: {
      game: {
        title: "Spillet",
        none: "Ikke noe spill ennå.",
        /** «Spill 3 · Grossist» */
        line: (game: string, role: string) => `${game} · ${role}`,
        name: (number: number | null) => gameName(number),
        /** Story 13.5: the finished Oppfølgingsspill that became the Student's game. [ASSUMPTION] */
        makeup: "Oppfølgingsspill",
        state: {
          not_ready: "Ikke klart ennå.",
          ready: "Ikke startet.",
          running: "Pågår.",
          finished: "Ferdig.",
          ended: "Avsluttet før siste uke.",
        } as Record<string, string>,
        /** «Ferdig ti. 12. des.» (the day ends in its own full stop) */
        finishedOn: (day: string) => `Ferdig ${sentence(day)}`,
        playedOut: "Spilt ut ved Spillfristen.",
        insight: "Se Spillinnsikt",
      },
      debrief: {
        title: "Debrief",
        explanation: "Forklaring",
        noExplanation: "Ingen Forklaring ennå.",
        /** «Sendt ti. 12. des.» */
        sent: (day: string) => `Sendt ${sentence(day)}`,
        notFinished: "Debriefen er ikke fullført.",
        /** «Fullført ti. 12. des. 3 nøkkeløyeblikk.» */
        finished: (day: string, moments: number) =>
          moments === 0 ? `Fullført ${sentence(day)}` : `Fullført ${sentence(day)} ${moments} nøkkeløyeblikk.`,
        late: "Etter Debrieffristen.",
        summary: "Se Debrief-sammendraget",
      },
      quiz: {
        title: "Debrief-quiz",
        none: "Ingen forsøk ennå.",
        /** One row: «Forsøk 2 · ti. 12. des. kl. 10:00 · bestått» */
        attempt: (number: number, at: string, passed: boolean) =>
          `Forsøk ${number} · ${at} · ${passed ? "bestått" : "ikke bestått"}`,
      },
      replay: {
        title: "Replay",
        none: "Ingen Replay ennå.",
        running: "Startet, ikke ferdig.",
        finishedOn: (day: string) => `Ferdig ${sentence(day)}`,
        insight: "Se Replay i Spillinnsikt",
      },
      test: {
        title: "Individuell test",
        none: "Ikke åpnet ennå.",
        status: {
          open: "Åpnet, ikke levert.",
          submitted: "Levert.",
          auto_submitted: "Levert automatisk ved Testfristen.",
        } as Record<string, string>,
        /** «Levert ti. 12. des. kl. 10:00.» */
        submittedAt: (at: string) => `Levert ${at}.`,
        partsTitle: "Deler med svar",
        parts: {
          choice: "Flervalg",
          interactive: "Interaktive oppgaver",
          long: "Langsvar",
          adapted: "Tilpassede oppgaver",
        } as Record<string, string>,
        answered: "har svar",
        unanswered: "mangler svar",
      },
      /** Until Story 12.5's «KI-vurdering» block takes this place. */
      assessment: {
        title: "KI-vurdering",
        states: {
          off: "KI-vurdering er slått av for denne klasseøkten.",
          not_ready: "KI-vurderingen er ikke klar.",
        } as Record<string, string>,
      },
    },
    /** The block (EXPERIENCE.md → Tilrettelegging): the idle lines, the form, «Lagret. Gjelder fra
     * nå.» are the spine's; the refusals and the failure are [ASSUMPTION] draft copy. */
    adjustment: {
      title: "Tilrettelegging",
      none: "Ingen tilrettelegging.",
      /** «Mer tid: 2 ×.» */
      moreTime: (factor: string) => `Mer tid: ${factor}.`,
      /** «Andel uker: 60 %.» */
      share: (percent: string) => `Andel uker: ${percent}.`,
      change: "Endre tilrettelegging",
      factorLegend: "Mer tid før KI tar over",
      asClass: "Som klassen",
      shareLabel: "Andel uker som kreves",
      /** The help line: «Klassen: 80 %.» */
      classShare: (percent: string) => `Klassen: ${percent}.`,
      /** «Skriv et helt tall fra 0 til 80.» */
      shareError: (max: number) => `Skriv et helt tall fra 0 til ${max}.`,
      /** «Gjelder bare Jonas, fra nå. Ingen andre studenter ser det. Endringen logges.» */
      scope: (name: string) => `Gjelder bare ${name}, fra nå. Ingen andre studenter ser det. Endringen logges.`,
      save: "Lagre tilrettelegging",
      cancel: "Avbryt",
      saved: "Lagret. Gjelder fra nå.",
      refusals: {
        invalid_adjustment: "Sjekk feltene.",
      } as Record<string, string>,
      failed: "Tilretteleggingen ble ikke lagret. Prøv igjen.",
    },
    /** The block «Frister» (Story 11.13, FR-18): one Student's own Test deadline, the Debrief
     * deadline moved with it. EXPERIENCE.md gives none of these strings: all [ASSUMPTION] draft
     * copy, listed for the founder's review. Times are Europe/Oslo. */
    deadline: {
      title: "Frister",
      /** «Testfrist: ti. 22. des. kl. 10:00.» */
      test: (at: string) => `Testfrist: ${at}.`,
      /** «Debrieffrist: …» */
      debrief: (at: string) => `Debrieffrist: ${at}.`,
      noTest: "Klasseøkta har ingen testfrist.",
      /** Shown when extended: «Forlenget. Klassens testfrist: …» */
      extended: (at: string) => `Forlenget. Klassens testfrist: ${at}.`,
      asClass: "Som klassen.",
      change: "Forleng testfrist",
      submitted: (name: string) => `${name} har levert testen. Fristen kan ikke forlenges.`,
      fieldLabel: "Ny testfrist",
      /** The help line under the field: «Må være etter klassens testfrist, …» */
      hint: (at: string) => `Må være etter klassens testfrist, ${at}.`,
      /** «Debrieffristen flyttes like mye. Gjelder bare Jonas. Endringen logges.» */
      scope: (name: string) => `Debrieffristen flyttes like mye. Gjelder bare ${name}. Endringen logges.`,
      save: "Lagre frist",
      cancel: "Avbryt",
      /** The result line that replaces the form: «Lagret. Ny testfrist for Jonas: …» */
      saved: (name: string, at: string) => `Lagret. Ny testfrist for ${name}: ${at}.`,
      /** On the field. */
      errors: {
        required: "Velg dato og klokkeslett.",
        not_later: (at: string) => `Velg en tid etter klassens testfrist, ${at}.`,
        passed: "Velg en tid som ikke har passert.",
      },
      refusals: {
        attempt_submitted: "Studenten har levert testen. Fristen kan ikke forlenges.",
        no_test_deadline: "Klasseøkta har ingen testfrist å forlenge.",
      } as Record<string, string>,
      failed: "Fristen ble ikke lagret. Prøv igjen.",
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

  /** The Meldingsskjema (Story 7.9, FR-40, UX-DR46): a one-way Message from staff to Students.
   * «Send Melding», «Meldingen er sendt til 4 studenter.» and «Sendt tidligere: 3» are the spine's;
   * the rest is [ASSUMPTION] draft copy. */
  messages: {
    crumb: "Melding",
    /** The page title names the recipient: «Melding til Noah, Spill 2». */
    title: {
      student: (name: string, game: number | null) =>
        game === null ? `Melding til ${name}` : `Melding til ${name}, ${gameName(game)}`,
      classGame: (game: number | null) => `Melding til ${gameName(game)}`,
      classSession: (session: number) => `Melding til alle i Klasseøkt ${session}`,
    },
    /** A Student whose name the api no longer gives. */
    unknownStudent: "studenten",
    /** Who gets it, under the title. */
    reach: (n: number) => (n === 1 ? "Meldingen går til 1 student." : `Meldingen går til ${n} studenter.`),
    noStudents: "Ingen studenter får denne meldingen nå.",
    field: "Melding",
    /** Under the field: the length limit and the one-way rule. */
    hint: (max: string) => `Høyst ${max} tegn. Studentene får meldingen her og på e-post, og kan ikke svare.`,
    send: "Send Melding",
    sending: "Sender …",
    sent: (n: number) => (n === 1 ? "Meldingen er sendt til 1 student." : `Meldingen er sendt til ${n} studenter.`),
    sentBefore: (n: number) => `Sendt tidligere: ${n}`,
    /** After a send: one more Message to the same recipient. */
    writeAnother: "Skriv en ny melding",
    tooLong: (max: string) => `Meldingen er for lang. Høyst ${max} tegn.`,
    empty: "Skriv en melding først.",
    /** The Lenke in the Oversikt header: worded unlike the Varselbånd's «Send Melding». */
    toSession: "Skriv melding til alle",
    /** On Spillinnsikt: to the whole Class game, and beside a Student's Seat. */
    toGame: "Melding",
    toStudent: "Melding",
    /** The accessible names of those two, which read the same on screen. */
    toGameLabel: (game: number | null) => `Melding til alle i ${gameName(game)}`,
    toStudentLabel: (name: string) => `Melding til ${name}`,
    /** Story 7.10: the Student's Messages on Hjem. No read state, no reply. [ASSUMPTION] */
    mine: {
      title: "Meldinger",
      /** When the sender's account is gone. */
      unknownSender: "Faglærer",
      /** The polite announcement of Messages that arrived while Hjem was open. */
      arrived: (sender: string, n: number) => (n === 1 ? `Ny melding fra ${sender}.` : `Nye meldinger: ${n}.`),
    },
    /** Story 7.10: «Meldinger», what a Class session was sent, for its staff. [ASSUMPTION] */
    sentList: {
      title: "Meldinger",
      crumb: "Meldinger",
      /** The Lenke in the Oversikt header and under the Meldingsskjema. */
      link: "Meldinger",
      fromForm: "Se sendte meldinger",
      session: (number: number, className: string) => `Klasseøkt ${number} · ${className}`,
      empty: "Ingen meldinger er sendt i denne Klasseøkten ennå.",
      to: {
        student: (name: string, game: number | null) =>
          game === null ? `Til ${name}` : `Til ${name}, ${gameName(game)}`,
        formerStudent: "Til en tidligere student",
        classGame: (game: number | null) => `Til ${gameName(game)}`,
        classSession: (session: number) => `Til alle i Klasseøkt ${session}`,
        list: (n: number) => (n === 1 ? "Til 1 student" : `Til ${n} studenter`),
      },
      from: (sender: string) => `Fra ${sender}`,
      reach: (n: number) => (n === 1 ? "Sendt til 1 student" : `Sendt til ${n} studenter`),
      /** Back to the Meldingsskjema for the same recipient; its accessible name says whom. */
      writeAgain: "Skriv ny melding",
      writeAgainLabel: (recipient: string) => `Skriv ny melding ${recipient.charAt(0).toLowerCase()}${recipient.slice(1)}`,
    },
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
    /** Story 6.4: the event stream missed its heartbeat, so the page may not show the latest
     * changes; followed by «Sist oppdatert 21:14». [ASSUMPTION] */
    stale: "Siden oppdateres ikke av seg selv akkurat nå.",
    pageError: "Siden kunne ikke lastes.",
    retry: "Prøv igjen",
    /** «Sist oppdatert 21:14»: the time live values were last read. */
    lastUpdated: (clock: string) => `Sist oppdatert ${clock}`,
    actionFailed: "Det ble ikke lagret. Prøv igjen.",
  },
} as const;
