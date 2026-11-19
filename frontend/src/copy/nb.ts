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

/** The Start-date line of «Du er invitert» and Hjem (Story 4.5). [ASSUMPTION] EXPERIENCE.md's draft:
 * a Student sees game, Role and Seats from the Start date (founder decision 2026-11-12). */
const START_DATE_LINE = "Du får Rolle og spill på startdatoen.";

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
      week: "Uke",
      // The mockup's row label for the Seat's own order (01-landing.png).
      yourOrder: "Din ordre",
      // [ASSUMPTION] Story 3.13: the mockup's note, without the line about the graph's time axis.
      ownNumbers: "Studenten ser bare sine egne tall.",
      demoData: "Demodata",
      classCurves: "Lagerkurvene for hele klassen ser du først når du er logget inn.",
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
      addLecturerSubmit: "Legg til Faglærer",
      inviteAssistant: "Inviter Assistent",
      inviteAssistantTitle: "Inviter en Assistent",
      assistantScope: "Assistenten får tilgang bare til denne Klassen.",
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
        `${count} ${count === 1 ? "Invitasjon sendt. Gyldig" : "Invitasjoner sendt. Gyldige"} til og med ${lastDay}.`,
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
