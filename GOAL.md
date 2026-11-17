/goal Bygg alle stories i ØL-spillet etter kjøreboka `.docs/implementation-artifacts/autobuild-runbook.md`. Les den først, og les den på nytt etter hver komprimering eller omstart. `sprint-status.yaml` avgjør hva som er neste story. Hver story bygges av én blokkerende underagent som kjører skillen `bmad-build-auto`. Bygg på grenen `epic-<N>`, commit og push etter hver story, og merge epicet til `main` når CI er grønn. Løs blokkerte stories selv, og før beslutningene i et issue. Stories som trenger grunnleggeren settes til `review` med et issue. Spør ingen.

Målet er nådd når alt dette stemmer:
1. Hver story i `sprint-status.yaml`, utenom 3.15, 15.10 og 15.14, står som `done` eller `review`, eller som `blocked` etter tre forsøk med et issue.
2. Alle epics står som `done` og er merget til `main`, og CI er grønn på `main`.
3. Siste seksjon i loggfila for kjøringen lister alle stories i `review` og `blocked`, med issuene.



Stopp også, og skriv hvorfor i loggfila, hvis noe av dette skjer:
- en handling krever en konto, en betaling eller en produksjonstjeneste
- en sperreregel stopper et steg som ikke kan gjøres på en annen måte
- CI på `main` er rød og fem forsøk på å rette den har feilet
- fem stories på rad ender som `blocked`