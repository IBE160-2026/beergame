# Story 10.1 visual check (commit 86a4606), Klasseøkt «Replay-scenario» block

Files: klasseokt-<state>-<width>.png (full page) and replay-block-<state>-<width>.png (the block only). States: for-lock, locked. Widths: 390, 1280, 1280-text200 (html font-size 200 %).

- klasseokt-for-lock-390 / -1280 / -1280-text200: whole Klasseøkt before the lock, block between Debrief/Obligatorisk and «Lagre Klasseøkt'. Block matches spec; no horizontal page scroll at any width.
- klasseokt-locked-390 / -1280 / -1280-text200: after the lock; lock line names «Replay-scenario»; block is plain text rows. Matches. No page overflow.
- replay-block-*: the block alone; ranges («Uke 5 til 12», «30 til 40»), «4, deretter 8, ± 2 hver uke» read in full, nothing cut off in the block. Matches copy in nb.ts.
- Mockup: 02-laerer-klasse is «Lag Klasse», there is no Klasseøkt mockup; DESIGN.md/EXPERIENCE.md tokens used for judgement only.
