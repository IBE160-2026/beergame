# Story 5.18 — skjermbilder (visuell kontroll)

Tatt 2026-11-20 mot lokal stack (`FEATURE_RERUN` på), innlogget som faglaerer@example.com, med ferske Klasser laget gjennom api-et: «IBE160 høst 2025 …» (arkivert, Klasseøkt 1 med startdato), «IBE160 vår 2026 …» (Klasseøkt 1 med startdato, Klasseøkt 2 uten) og målklassen «IBE160 høst 2026 …». Kildelisten tar også med demolærerens andre Klasser fra tidligere kjøringer. 390 px-kjøringen laget en kopi i målklassen, så 1280 px-kjøringen ser den som nyeste kilde.

- `klasse-lenke-390.png` / `-1280.png` — Klasse-siden med «Lag Klasseøkt» og Lenken «Lag fra en tidligere Klasseøkt».
- `kopipanel-kilder-390.png` / `-1280.png` — panelet åpent: «Klasseøkt å kopiere», Bryteren, hva som kopieres og ikke, «Lag kopi» (eneste primærknapp) og «Avbryt».
- `kopipanel-liste-utfoldet-390.png` / `-1280.png` — kildelisten vist utfoldet (select satt til `size` i skriptet, siden en åpen innebygd liste ikke kan fotograferes): grupper per Klasse, «(arkivert)» på den arkiverte.
- `kopipanel-behold-etterspørsel-390.png` / `-1280.png` — Bryteren på: «Den samme som i Klasseøkten du kopierer».
- `kopipanel-feil-390.png` / `-1280.png` — feil (stubbet 422 `invalid_settings`): «Innstillingene i den gamle Klasseøkten godtas ikke lenger …» under knappene.
- `klasseokt-kopiert-390.png` / `-1280.png` — den nye Klasseøkten med «Kopiert fra Klasseøkt N i {klasse}.» i stedet for standardlinjen.
- `klasseokt-innsatsniva-erstattet-390.png` / `-1280.png` — samme Klasseøkt med stubbet `effort_level_replaced` (Grundig) og `ai_mode: llm`: «Innsatsnivået Grundig finnes ikke for den nye modellen. Klasseøkten bruker standardnivået standard.»

Kontrollert i skriptet på alle skjermer: ingen sidelengs rulling, ingen mål under 44 px i `main`, ingen tekst under 13 px, høyst én primærknapp.
