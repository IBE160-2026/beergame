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
      } as Record<string, string>,
      /** What an action concerns, by its target key. */
      targets: {
        user_id: (label: string) => label,
        invitation_id: (label: string) => `Invitasjon til ${label}`,
        institution_id: (label: string) => label,
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
        },
        // [ASSUMPTION] Story 3.7.
        failed: "Invitasjonen ble ikke sendt. Prøv igjen.",
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
