# Story 5.11 – visuell kontroll

Fersk Faglærer (fra Invitasjon) og fersk Klasse via api, nb-NO, Europe/Oslo, Datoer +3/+17/+20/+27 dager. Låst tilstand er et falsket GET-svar (`locked`, `locked_at`, `passed_dates`, for Assistent også `can_manage: false`), slik `class-session-lock.spec.ts` gjør; ingen api-rute låser. Sammenlignet med mockup 03, DESIGN.md og EXPERIENCE.md. Ingen side ruller sidelengs på 390 px, ingen tekst under 13 px i `main`, høyst én primærknapp. Ingen visuelle rettinger var nødvendige.

- `klasseokt-ulast-{390,1280}.png` – ulåst til sammenligning: Valgknapper, Bryter, datofelt, «Endre spillinnstillinger», «Lagre Klasseøkt» nederst. Stemmer med mockup 03.
- `klasseokt-last-frister-{390,1280}.png` – låst, Startdato passert: «Låst ma. 23. nov. kl. …» under tittelen, alle frosne verdier som tekst, Startdato som tekst med «Passert. Datoen kan ikke flyttes.», tre frister som felt, «Lagre frister» med hint under feltene i Datoer, ingen «Lagre Klasseøkt». Stemmer (Issue #103).
- `klasseokt-last-alle-passert-{390,1280}.png` – låst, alle datoer passert: alle fire som tekst med «Passert», linjen «Labtimer kan fortsatt endres.», ingen lagreknapp. Stemmer.
- `klasseokt-last-venter-{390,1280}.png` – Startdato passert, låsen ikke kjørt ennå (`locked_at: null`): linjen «Startdatoen er passert. … kan ikke endres.», ellers som over. Stemmer.
- `klasseokt-last-assistent-{390,1280}.png` – låst sett uten rett til å endre: alt som tekst, ingen lagreknapp, ingen «Legg til Labtime», ingen «kan fortsatt endres»-linje. Stemmer. (Assistent-ingressen vises ikke fordi rollen er falsket via `can_manage`, ikke en ekte Assistent.)
- `klasseokt-last-fordeling-{390,1280}.png` – låst med lagret utkast (5 studenter, 2 spill), «Fordeling» åpnet: diagram og spillinje, ingen «Kjør fordeling på nytt», ingen «Bekreft fordeling», ingen «Flytt». «Lagre frister» er eneste primærknapp (Visning-velgerens valgte segment er en tilstand, ikke en handling). Stemmer.
- Avvist-lås-varselet (mail `class_session_lock_refused`) er ikke tatt: lokalt svarer mock-leverandøren alltid, så låsen avvises bare i produksjon og dev-postkassen har ingen slik mail.

Kjente, ikke rettet (vurdert tidligere i triage, utenfor historien): datofeltene viser amerikansk format i headless Chromium (native `datetime-local`); i låst-linjen på 1280 px står «frosset.» alene på andre linje.
