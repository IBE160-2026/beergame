# Story 10.9 visual check (Epic 10 close-out), route /klasseokter/{id}, block «Replay-scenario»
Lane 2 stack (port 8081), Chromium with --lang=nb-NO, a fresh Lecturer and Class session per shot. Shots are of the block only.
Widths: 390, 1280, 200 (1280 px wide with html font-size 200 %). The local stack has FEATURE_INFO_VISIBILITY on; «flag off» is the api's answer with `info_visibility_enabled: false` (the 422 is pinned by the api tests).

- views-off-{390,1280,200}.png: «Eget scenario» opened; under «Synlige naboer» the two Bryter «Leddet oppstrøms» and «Leddet nedstrøms», both «Nei» as in the Class session, with the Replay help text. Matches.
- views-both-warnings-{390,1280,200}.png: both switched on; judged at once; one warning per view («Advarsel: Replay viser lager og restordre hos leddet oppstrøms/nedstrøms, som Klassespillene ikke viser. Det gjør trolig Replay lettere.»). Matches.
- views-readonly-{390,1280,200}.png: saved, then read as an Assistant lecturer (`can_manage` false): the row «Synlige naboer: Begge naboene» with both warnings, no controls. Matches.
- flag-off-{390,1280,200}.png: flag off: no «Synlige naboer», no switch, no help text; the rest of the own form as before. Matches.
No horizontal scroll and nothing cut off in any shot. The block is capped at max-w-4xl (two columns from 1024 px).
