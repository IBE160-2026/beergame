# Story 4.7 — visual check

The Class page `class-of-1994` (faglaerer@example.com), with `GET /registrations` and `POST /reminders` faked as a 25-row Class (16 registered, 2 manual, 2 invited, 1 renewal request, 1 hard bounce, 1 soft bounce, 2 expired), except `klasse-real-demo`, which is the live stack. The «Invitasjoner» counts above are the live ones, so they do not add up to the faked list. Compared with mockup `02-laerer-klasse.png`, DESIGN.md and EXPERIENCE.md. Taken after the fix (2 px bar gap).

| Screenshot | Shows | Matches |
|---|---|---|
| klasse-status-mix-390.png | Bar, «Registrert 16 · Manuelt 2 · Uregistrert 7», link wrapped below, stacked rows | Yes |
| klasse-status-mix-1280.png | Same; link right-aligned on the key row as in mockup 02; three-column rows | Yes (Uregistrert segment in `axis` is 1.61:1 against `paper`, see note) |
| klasse-filter-invited-{390,1280}.png | Filter «Invitert»: 2 rows with last valid day | Yes |
| klasse-filter-renewal_requested-{390,1280}.png | Filter «Ba om ny Invitasjon»: 1 row with action | Yes |
| klasse-filter-bounced-{390,1280}.png | Filter «Kom ikke fram»: hard (no action) and soft (action) | Yes |
| klasse-filter-unregistered-{390,1280}.png | Filter «Uregistrert, Invitasjonen er utløpt»: 2 rows | Yes |
| klasse-filter-registered-{390,1280}.png | Filter «Registrert»: 16 rows, no actions | Yes |
| klasse-filter-registered_manually-{390,1280}.png | Filter «Registrert manuelt»: 2 rows | Yes |
| klasse-search-{390,1280}.png | Search «BER»: case-insensitive match, «Viser N av 25 adresser.» | Yes |
| klasse-search-none-{390,1280}.png | Search with no match: «Ingen adresser passer til søket.» | Yes |
| klasse-remind-confirm-{390,1280}.png | In-place confirmation: lead, «1 adresse med permanent feil får ingen påminnelse.», validity 14, one primary «Send 6 påminnelser», «Avbryt» | Yes |
| klasse-remind-invalid-{390,1280}.png | Validity «abc» refused with the range error | Yes |
| klasse-remind-sent-{390,1280}.png | Result line «6 påminnelser sendt. Gyldige til og med …» and the hard bounce named | Yes |
| klasse-resend-confirm-{390,1280}.png | Row confirmation under its row, title with the address, primary «Send ny Invitasjon» | Yes |
| klasse-resend-sent-{390,1280}.png | «Ny Invitasjon sendt til … Gyldig til og med …» | Yes |
| klasse-hard-row-{390,1280}.png | Hard-bounced row: «Kom ikke fram, permanent feil», no button | Yes |
| klasse-only-hard-{390,1280}.png | Only a hard bounce waits: «Uregistrert 1», link hidden | Yes (recorded decision: total counts it, no action) |
| klasse-all-registered-{390,1280}.png | All registered: bar in `lager` + `ink`, no link, no row actions | Yes |
| klasse-real-demo-{390,1280}.png | Live demo Class (33 entries from earlier e2e runs): «Manuelt 0» keeps its key with no segment (true zero) | Yes |

No horizontal scroll at 390 px in any state.

Notes needing a judgement:
- The Uregistrert segment and key are `axis` (#C3CDD8), 1.61:1 against `paper`, below the 3:1 non-text floor. Mockup 02 and the spec choose `axis`; the bar is `aria-hidden` and the totals are in text, so no information is lost.
- Mockup 02 places the section in the right column of «Lag Klasse»; the Class page is one column (layout from Stories 4.1–4.6).
