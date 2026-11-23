import { nb } from "@/copy/nb";

/**
 * Which home a User lands on, and which of the three homes they may open (Story 3.3, UX-DR77,
 * FR-2). The API enforces access on every request (`platform/authz`); this decides what the web
 * app shows, so a page a User may not open is never rendered for them.
 *
 * - A Lecturer lands on the Lærerhjem, also when they are Admin too (links lead both ways), and so
 *   does an Assistent (Story 4.9: the session role `assistant`), who sees only their Classes there.
 * - An Admin who is neither lands on the Admin-område.
 * - Every other User (a Student) lands on Hjem.
 */
export type Home = "adminArea" | "lecturerHome" | "home";

export type RoleHolder = { roles: readonly string[] };

export const HOME_PATH: Record<Home, string> = {
  adminArea: "/admin",
  lecturerHome: "/laererhjem",
  home: "/hjem",
};

/** «Brukere og roller» in the Admin-område (Story 3.7). */
export const ADMIN_USERS_PATH = "/admin/brukere";

/** «Institusjoner» in the Admin-område (Story 3.11). */
export const ADMIN_INSTITUTIONS_PATH = "/admin/institusjoner";

/** «Revisjonslogg» in the Admin-område (Story 3.12). */
export const ADMIN_AUDIT_PATH = "/admin/revisjonslogg";

/** «Mine data» (Story 15.1, FR-75): every User's own data, reached from Hjem. */
export const MY_DATA_PATH = "/mine-data";

/** «Pseudonymisert eksport» in the Admin-område (Story 15.4). */
export const ADMIN_EVALUATION_PATH = "/admin/evaluering";

/** «KI-kostnad» in the Admin-område (Story 15.5; Stories 15.6 and 15.7 extend it). */
export const ADMIN_AI_COST_PATH = "/admin/ki-kostnad";

/** «KI-kostnad per Klasseøkt» (Story 15.6): every Class session's AI cost and limit. */
export const ADMIN_AI_COSTS_PATH = `${ADMIN_AI_COST_PATH}/klasseokter`;

/** One Class session's AI cost and its limit (Story 15.6). */
export function adminAiCostPath(classSessionId: string): string {
  return `${ADMIN_AI_COSTS_PATH}/${encodeURIComponent(classSessionId)}`;
}

/** «Drift» in the Admin-område (Story 15.8): the Class sessions, and per Class session its errors,
 * fallback, AI response times, Play guard share and AI cost. */
export const ADMIN_OPERATIONS_PATH = "/admin/drift";

/** One Class session's «Drift» view (Story 15.8). */
export function adminOperationsPath(classSessionId: string): string {
  return `${ADMIN_OPERATIONS_PATH}/${encodeURIComponent(classSessionId)}`;
}

/** «Tverrinstitusjonell statistikk» in the Admin-område (Story 14.7, cut list): only while
 * `FEATURE_CROSS_INSTITUTION_STATS` is on (`SessionUser.cross_institution_stats`). */
export const ADMIN_CROSS_INSTITUTION_PATH = "/admin/tverrinstitusjonell-statistikk";

/** «Kontrolltest» in the Admin-område (Story 12.7). */
export const ADMIN_CONTROL_TESTS_PATH = "/admin/kontrolltest";

/** «Sensorer» of one Control test in the Admin-område (Story 12.9). */
export const controlTestScorersPath = (id: string) => `${ADMIN_CONTROL_TESTS_PATH}/${encodeURIComponent(id)}`;

/** «Resultater» of one Control test in the Admin-område (Story 12.10). */
export const controlTestResultsPath = (id: string) => `${controlTestScorersPath(id)}/resultater`;

/** «Sensur av Kontrolltest» (Story 12.9): the Control tests a named scorer scores, reached from
 * their own home; one Control test's answers, and one answer. */
export const SCORING_PATH = "/sensur";
export const scoringListPath = (id: string) => `${SCORING_PATH}/${encodeURIComponent(id)}`;
export const scoringAnswerPath = (id: string, answerId: string) =>
  `${scoringListPath(id)}/${encodeURIComponent(answerId)}`;

/** «Lag Klasse» (Story 4.1). */
export const NEW_CLASS_PATH = "/klasser/ny";

/** A Class's own page (Story 4.1). */
export const classPath = (id: string) => `/klasser/${encodeURIComponent(id)}`;

/** «Faglærere og assistenter» of a Class (Story 4.9). */
export const classStaffPath = (id: string) => `${classPath(id)}/faglaerere`;

/** A Class session's Klasseøkt screen (Story 5.1). */
export const classSessionPath = (id: string) => `/klasseokter/${encodeURIComponent(id)}`;

/** The Studentside of one Student of a Class session, for its Lecturers (Story 8.9). */
export const studentPagePath = (sessionId: string, userId: string) =>
  `${classSessionPath(sessionId)}/studenter/${encodeURIComponent(userId)}`;

/** The Oversikt of a Class session's Class games, for its staff (Story 7.1). */
export const classOverviewPath = (id: string) => `${classSessionPath(id)}/oversikt`;

/** The Klasserapport (Story 14.1): how the Class games went, for the Lecturers of the Class. */
export const classReportPath = (id: string) => `${classSessionPath(id)}/klasserapport`;

/** Tverrklasse-statistikk (Story 14.3): the Lecturer's Class sessions compared on stored aggregates. */
export const crossClassPath = "/tverrklasse-statistikk";

/** «Alle spill side om side» (Story 14.5): a Student's view of every Class game of their session. */
export const allGamesPath = (id: string) => `/alle-spill/${encodeURIComponent(id)}`;

/** «Start spill» (Story 8.10): every Class game of the session that has not started, for its
 * Lecturers. */
export const startGamesPath = (id: string) => `${classOverviewPath(id)}/start`;

/** «Sett inn KI-spillere» (Story 8.12): every Seat the Class session's games wait for, for its
 * Lecturers. */
export const fillSeatsPath = (id: string) => `${classOverviewPath(id)}/sett-inn`;
/** «Alle spill i plenum» (Story 14.6): the Oversikt's games for the projector. */
export const plenaryPath = (id: string) => `${classOverviewPath(id)}/plenum`;

/** The Oversikt after «Sett inn 9 KI-spillere» (Story 8.12): it reads «9 KI-spillere er satt inn.»
 * once. */
export const overviewFilledPath = (id: string, inserted: number) =>
  `${classOverviewPath(id)}?satt-inn=${encodeURIComponent(String(inserted))}`;

/** The Oversikt after «Start 12 spill» (Story 8.10): it reads «12 spill er startet.» once. */
export const overviewStartedPath = (id: string, started: number) =>
  `${classOverviewPath(id)}?startet=${encodeURIComponent(String(started))}`;

/** The Oversikt again, back from Spillinnsikt (Story 7.7): focus returns to the game `gameId`, in
 * the wall or, with `view` «tabell», in «Vis som tabell». */
export const overviewReturnPath = (id: string, gameId: string, view: "wall" | "table" = "wall") =>
  `${classOverviewPath(id)}?spill=${encodeURIComponent(gameId)}${view === "table" ? "&visning=tabell" : ""}`;

/** Spillinnsikt: one Class game week by week, for the staff (Story 7.7); opened from «Vis som
 * tabell», it says so, so its Oversikt crumb returns to the table. */
export const gameInsightPath = (sessionId: string, gameId: string, view: "wall" | "table" = "wall") =>
  `${classOverviewPath(sessionId)}/spill/${encodeURIComponent(gameId)}${view === "table" ? "?visning=tabell" : ""}`;

/** The Meldingsskjema (Story 7.9): to the whole Class session, a Class game (`game`), one
 * Student (`student`, with the game it is written from, if any), or (Story 13.6, `requirement`)
 * the Students who have not met the requirement. */
export const messagePath = (sessionId: string, to: { game?: string; student?: string; requirement?: true } = {}) => {
  const params = new URLSearchParams();
  if (to.requirement) params.set(REQUIREMENT_PARAM, REQUIREMENT_VALUE);
  if (to.game) params.set("spill", to.game);
  if (to.student) params.set("student", to.student);
  const query = params.toString();
  return `${classSessionPath(sessionId)}/melding${query ? `?${query}` : ""}`;
};

/** The Meldingsskjema's query for Story 13.6's recipient: `?krav=ikke-oppfylt`. */
export const REQUIREMENT_PARAM = "krav";
export const REQUIREMENT_VALUE = "ikke-oppfylt";

/** «Meldinger» (Story 7.10): the Messages a Class session was sent, for its staff. */
export const sentMessagesPath = (sessionId: string) => `${classSessionPath(sessionId)}/meldinger`;

/** The Adapted item preview with a sample Student (Story 11.9), for the Class session's staff. */
export const adaptedPreviewPath = (sessionId: string) => `${classSessionPath(sessionId)}/tilpassede-oppgaver`;

/** A Student's «Velg spill og sete» in a Class session with Student choice (Story 5.17). */
export const seatChoicePath = (id: string) => `${classSessionPath(id)}/velg-sete`;

/** A Student's Class game (Epic 6), and its «Regler før første ordre» (Story 6.2). */
export const gamePath = (id: string) => `/spill/${encodeURIComponent(id)}`;
export const rulesPath = (id: string) => `${gamePath(id)}/regler`;
export const startingTaskPath = (id: string) => `${gamePath(id)}/startoppgave`;
/** The Replay-gjennomgang of a finished Replay (Story 10.7 builds the page; Story 10.5's
 * «Gå til gjennomgangen» leads there). */
export const walkthroughPath = (id: string) => `${gamePath(id)}/gjennomgang`;

/** The Student's Debrief in a Class session (Story 9.2): where «Gå til Debrief» on «Spillet er
 * ferdig» and Stegene's Debrief step lead. One Debrief per Student and Class session. */
export const DEBRIEF_PATH = (classSessionId: string) => `/debrief/${encodeURIComponent(classSessionId)}`;

/** The Student's Individual test in a Class session (Story 11.3): where Stegene's current test
 * step leads. One attempt per Student and Class session. */
export const TEST_PATH = (classSessionId: string) => `/individuell-test/${encodeURIComponent(classSessionId)}`;

/** The Student's «KI-vurdering» of their Individual test in a Class session (Story 12.2), linked
 * from Hjem once the test step is done. */
export const ASSESSMENT_PATH = (classSessionId: string) => `/ki-vurdering/${encodeURIComponent(classSessionId)}`;

/** A Student's Explanation and Debrief summary for the Class's staff (Story 9.8), where
 * Spillinnsikt's links lead (`debrief.insight` in the api builds the same path). */
export const studentDebriefPath = (classSessionId: string, studentId: string) =>
  `${classSessionPath(classSessionId)}/studenter/${encodeURIComponent(studentId)}/debrief`;

/** The link that leads to each home («Til Lærerhjem» …). */
export const HOME_LINK: Record<Home, string> = {
  adminArea: nb.navigation.toAdminArea,
  lecturerHome: nb.navigation.toLecturerHome,
  home: nb.navigation.toHome,
};

const isAdmin = (user: RoleHolder) => user.roles.includes("admin");
const isLecturer = (user: RoleHolder) => user.roles.includes("lecturer");
const isAssistant = (user: RoleHolder) => user.roles.includes("assistant");
const isStaff = (user: RoleHolder) => isLecturer(user) || isAssistant(user);

/** Whether `user` may create a Class: a Lecturer, never an Assistent (Story 4.9). */
export const canCreateClass = isLecturer;

/** Whether `user` may open a Class page and its Klasseøkt (Stories 4.1, 5.1): the staff, and an
 * Admin, who owns the Control test Classes they set up (Story 12.7). The api decides which Class
 * (`platform/authz`); any other reads as the permission-denied page. */
export function canOpenClasses(user: RoleHolder): boolean {
  return isStaff(user) || isAdmin(user);
}

export function homeOf(user: RoleHolder): Home {
  if (isStaff(user)) return "lecturerHome";
  if (isAdmin(user)) return "adminArea";
  return "home";
}

/** The crumbs before a Class and its Klasseøkt: the Lærerhjem for its staff; for a Control test
 * Class whose owner holds no staff role, only the Admin's, the Admin-område and «Kontrolltest»
 * (Story 12.7), where they reached it. */
export function classCrumbs(user: RoleHolder, controlTest: boolean) {
  if (controlTest && homeOf(user) === "adminArea") {
    return [
      { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
      { label: nb.admin.controlTests.title, href: ADMIN_CONTROL_TESTS_PATH },
    ] as const;
  }
  return [{ label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome }] as const;
}

/** Whether `user` may open `page`. Hjem is the home of a User with no staff role. */
export function canView(page: Home, user: RoleHolder): boolean {
  switch (page) {
    case "adminArea":
      return isAdmin(user);
    case "lecturerHome":
      return isStaff(user);
    case "home":
      return !isAdmin(user) && !isStaff(user);
  }
}
