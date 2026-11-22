# Story 10.2 visual check, commit e7942c1, route /klasseokter/{id}, block "Replay-scenario"
Files: replay-<state>-<width>.png (full page) and replay-<state>-block-<width>.png (the block only). Widths: 390, 1280, 200 (= 1281 px wide with html font-size 200 %).
States and match against DESIGN/EXPERIENCE:
- standard: default scenario as Valgknapper + word list + hidden line. Matches, except heading size (see below).
- own-opened: Eget scenario prefilled, guided-weeks warning under "Veiledede uker". One column at 390, two at 1280 and 200 %. Matches.
- errors: weeks min 40 / max 30, order delay 9, change week 99. Only ONE error shown (weeks, "Må være fra 40 til 30"); the delay and change-week errors are missing. Deviation.
- warnings-range: delay 1 warning under Ordreforsinkelse, weeks 30-40, change week 5-12. Matches.
- saved: "Klasseøkten er lagret." under the one primary button. Matches.
- reloaded: own scenario read back from the api. Matches.
- assistant (can_manage false, mocked): read-only list with warnings, no controls. Matches.
- locked (dev lock route): read-only list with warnings, no controls. Matches.
No horizontal scroll in any state at 390, 1280 or 200 %.
