# Story 8.11 visual check (5bb7bbd). Widths: 390, 1280, 1280-200 (200 % text). No horizontal page overflow in any shot.

- spillinnsikt-unavailable-<w>: Spillstyring outside a Labtime, disabled «Marker som i rommet», caption «Kan bare brukes i en Labtime.» above it. Matches.
- spillinnsikt-available-<w>: active secondary button. Matches.
- spillinnsikt-form-<w>: form in place, «Ventetid i rommet» (10) focused, help line, consequence line, primary «Marker som i rommet, 10 min», link «Avbryt». Matches (Avbryt is a link, not a button).
- spillinnsikt-form-error-<w>: value 1, error under field in red, primary reads «Marker som i rommet». Matches Ordrefelt pattern.
- spillinnsikt-result-<w> / -marked-<w>: «I rommet til 04:30. KI tar over etter 10 min uten ordre.» + «Ikke i rommet lenger» + result line «I rommet til 04:30.» below the button (result line shows after the action, duplicates the status line). Judgement.
- spillinnsikt-ended-<w>: after «Ikke i rommet lenger».
- spill-before-mark-<w>, spill-line-10min-<w>, spill-line-own-minutes-<w>: Student's Spill, bold ink line above «Setene» with 10 min. own-minutes variant identical: the Tilrettelegging call returned 403 in my script, so a different own-minutes value was not shown.
- hjem-while-marked-<w>: Student Hjem while marked; no line there (code only has it on Spill).
- oversikt-wall-<w>: row label «Spill 1 · I rommet» in the wall and the pink Venter group. Matches.
