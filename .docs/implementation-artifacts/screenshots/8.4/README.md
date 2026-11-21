Story 8.4 visual check, commit 48cd2bb. Stack olspillet-vis, stubbed envelopes as in reclaim.spec.ts. Widths 390 and 1280 (suffix -390/-1280), plus 200 % text at 390.
spill-taken-<w>: Spill, Seat taken over, note + secondary «Ta tilbake setet»; «Alle rader og kostnad» above the note; chain «KI-ordre 9» regular weight. Matches.
spill-refusal-<w>: 409 seat_not_yours, red inline line under the button, button stays. Matches.
spill-queued-<w>: after the press, «Du får setet tilbake når neste Uke åpner.» replaces the button. Matches.
spill-back-<w>: Seat back with the Student (next Uke), note gone, chain «Din ordre», order field. Matches 05-spill.
hjem-taken-<w>: Hjem, note + button, no Spillkort (by design, home.ts cardState). Matches spec; differs from 04 mockup only by the absent card.
hjem-refusal-<w>, hjem-queued-<w>: same states on Hjem. Match.
hjem-back-<w>: Spillkort and «Gå til Uke 11» primary return. Matches 04.
spill-taken-200pct-390, hjem-taken-200pct-390: 200 % text, no sideways page scroll; graph scrolls inside its own region («Sveip for tidligere uker»); chain labels wrap. Judgement only.
