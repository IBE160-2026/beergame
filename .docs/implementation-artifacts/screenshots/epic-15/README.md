# Epic 15: Personvern og drift (close-out visual check)

Taken once for the epic on the local stack (2026-11-23), at 390 px and 1280 px, full page. One
fresh Student in a running Class game (two Orders of their own); the "slettet" shots are the same
Class session after its deletion date was set in the past (no sweep run), so they show the state
from the date on. Checked against DESIGN.md, EXPERIENCE.md and the mockups.

Screenshot | what it shows | matches the design?

- `mine-data-{390,1280}.png` | «Mine data» (15.1): Studentrapport at the top, the categories with counts and «Vis» | matches; plain list, data first
- `mine-data-ordrer-{390,1280}.png` | «Ordrer» opened: each Order with Klasseøkt, time and fields | matches
- `hjem-slettedato-{390,1280}.png` | Hjem with the deletion date under «Rapport» (13.9, 15.3) | matches
- `hjem-slettet-{390,1280}.png` | Hjem after the date: «Dataene dine fra denne Klasseøkten er slettet.», Seats by Role («Deg») | fixed in the close-out (said «slettes 1. januar 2026. Last ned … før det» for a day gone by)
- `institusjoner-oppbevaring-{390,1280}.png` | «Institusjoner» with the retention period per Institution and the DPA line (15.3, 15.12) | matches; long at 390 only because the shared test database holds many Institutions
- `studentside-for-{390,1280}.png` | Studentside before the date | matches
- `studentside-slettet-{390,1280}.png` | Studentside after the date (409 `data_deleted`) | fixed in the close-out (no space under the heading)
- `spillinnsikt-for-{390,1280}.png`, `spillinnsikt-slettet-{390,1280}.png` | Spillinnsikt before and after the date: Seats by Role, no names | matches
- `oversikt-slettet-{390,1280}.png` | Oversikt after the date: «Fabrikk: Student», no names | matches
- `klasseokt-slettet-{390,1280}.png` | Klasseøkt after the date | matches (Epic 13's export block states the deletion)
- `spill-slettet-{390,1280}.png` | the Student's own game after the date: fellow Seats by Role | matches (names hidden since the close-out)
- `brukere-…`, `evaluering-…`, `ki-kostnad-…`, `drift-…`, `drift-klasseokt-…` | Admin pages of 15.2, 15.4, 15.6–15.8 | match; tables and figures, no decoration
- `tilgjengelighet-{390,1280}.png` | Tilgjengelighetserklæring (15.13) | matches
