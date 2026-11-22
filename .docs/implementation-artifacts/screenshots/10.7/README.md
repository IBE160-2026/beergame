Story 10.7 visual check, commit ff8792a, /spill/<id>/gjennomgang, stubbed api (shapes from replay-walkthrough.spec.ts). No horizontal page overflow in any shot (scrollWidth - clientWidth = 0).
gjennomgang-pending-390/1280.png - «Gjennomgangen lages.» plus a Skjelett of one bar and three rules; does not look like a chart; mostly matches copy, skeleton weak (judgement).
gjennomgang-ready-390/1280.png - totals, one chart (Replay blue/red with fill, Class game grey line, shared Uke axis, ticks Uke 1/12/24/36), legend text, «Ikke like for like.» with three reasons, AI-marked line, two moments; matches except no direct line labels, no y-axis unit.
gjennomgang-code-390/1280.png - same chart and numbers, line without KI prefix; matches.
gjennomgang-mostlyai-390/1280.png - Replay-only chart «Netto lager, Replay», mostlyAi sentence, no Class total, no «Ikke like for like.»; matches (third moment is a duplicate stub id).
gjennomgang-table-390/1280.png - «Vis som tabell»: Uke + Netto lager/Ordre/Kostnad per run; scrolls inside its own region (about 8-9 rows visible, 36 in all); matches. The «–» rows (Uke 33-36) are below the visible window and not captured.
gjennomgang-closed-390/1280.png - «Replay stengt» message from Story 10.6; matches.
gjennomgang-notfinished-390/1280.png - «Gjennomgangen kommer når Replay er ferdig.» with link «Til Replay»; matches.
gjennomgang-other-390/1280.png - real 403: «Du har ikke tilgang til denne siden.» with «Til Hjem»; matches.
gjennomgang-ready-390-200pct.png, gjennomgang-table-390-200pct.png, gjennomgang-mostlyai-390-200pct.png - html font-size 200%; text reflows, no page overflow; chart SVG labels do not grow with text (judgement).
