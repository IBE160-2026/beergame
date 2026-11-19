# Story 4.5 – visual check (390 and 1280 px)

Compared with mockup 04 (left, «Registrering»), DESIGN.md and EXPERIENCE.md. Taken after the fix «E-post, fra klasselisten». The demo Lecturer is called «Demo Faglærer», so the lead reads «Faglærer Demo Faglærer …». That comes from the data, not the copy.

- `invitert-empty-{390,1280}.png`: «Du er invitert» for a new Student, with the Class, course code, inviting Lecturer, the locked address «E-post, fra klasselisten», «Minst 8 tegn.», one primary button and the validity and Start-date line. Matches, apart from the missing «Har du konto? Logg inn» line (see deviations).
- `invitert-errors-{390,1280}.png`: the first press with empty fields. «Skriv navnet ditt.» and «Skriv et passord.» show in restordre, and focus is on Navn. Matches.
- `invitert-errors-password-{390,1280}.png`: once a name is typed its error clears, and a 4-character password reads «Passordet må ha minst 8 tegn.». Matches.
- `hjem-one-class-{390,1280}.png`: Hjem after registering, with «class-of-1994, IBE160» as an h2 on a hairline list and «Du får Rolle og spill på startdatoen.». Matches the EXPERIENCE «Hjem before the Start date» state. Stegene are not drawn yet (Epic 6).
- `hjem-two-classes-{390,1280}.png`: the same Student after joining a second Class, with both Classes and the line under each. Matches.
- `invitert-existing-{390,1280}.png`: an existing account invited to a second Class. The page reads «Adressen har allerede en konto. Logg inn, så blir du med i …», asks for the password, and offers «Logg inn og bli med i Klassen» and «Glemt passord?». Matches the spec.
- `invitert-wrong-password-{390,1280}.png`: a wrong password gives «Feil e-post eller passord.» above the button. Matches.
- `invitert-used-{390,1280}.png`: a used Student link shows «Lenken er utløpt eller brukt.» between rules, with the secondary button «Be om ny Invitasjon». Matches the Epic 3 state.
- `invitert-expired-{390,1280}.png`: an unknown or expired token shows the same state. A real expired link could not be made on the stack without changing the clock or the database.
- `invitert-renewal-requested-{390,1280}.png`: the result line replaces the state it answers, and focus moves to it. Matches.
- `klasse-forbidden-{390,1280}.png`: a Student opening a Class address gets «Du har ikke tilgang til denne siden.» and «Til Hjem». `GET /api/classes/enrolled/{other}` answered 403. Matches.

No page scrolls sideways at 390 px, and every page has at most one primary button.

Deviations left for a judgement:
- Mockup 04 has «Har du konto? Logg inn» under the form, and the page has no such line. The page already switches to the login form when the address has an account, and a link to «Logg inn» would lose the Invitation.
- The rest of the app writes the Roster as «Klasselista», capitalised (Stories 4.3 and 4.4). Only this label now follows EXPERIENCE.md's drawn «klasselisten».
- The existing-account lead does not name the inviting Lecturer. The new-account lead does.
