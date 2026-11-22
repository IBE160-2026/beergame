"""The Debrief (Epic 9, FR-41 to FR-47, AD-21). `debrief.commands` is the only writer of its
tables; `debrief.rules` decides whether a Student's Debrief is open; other modules read it through
`debrief.service`. Never imports `modules/players`, so the Debrief works under any AI mode."""
