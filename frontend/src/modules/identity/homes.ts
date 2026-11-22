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

/** «Pseudonymisert eksport» in the Admin-område (Story 15.4). */
export const ADMIN_EVALUATION_PATH = "/admin/evaluering";

/** «KI-kostnad» in the Admin-område (Story 15.5; Stories 15.6 and 15.7 extend it). */
export const ADMIN_AI_COST_PATH = "/admin/ki-kostnad";

/** «Drift» in the Admin-område (Story 15.8): the Class sessions, and per Class session its errors,
 * fallback, AI response times, Play guard share and AI cost. */
export const ADMIN_OPERATIONS_PATH = "/admin/drift";

/** One Class session's «Drift» view (Story 15.8). */
export function adminOperationsPath(classSessionId: string): string {
  return `${ADMIN_OPERATIONS_PATH}/${encodeURIComponent(classSessionId)}`;
}

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

/** «Start spill» (Story 8.10): every Class game of the session that has not started, for its
 * Lecturers. */
export const startGamesPath = (id: string) => `${classOverviewPath(id)}/start`;

/** «Sett inn KI-spillere» (Story 8.12): every Seat the Class session's games wait for, for its
 * Lecturers. */
export const fillSeatsPath = (id: string) => `${classOverviewPath(id)}/sett-inn`;

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

/** The Meldingsskjema (Story 7.9): to the whole Class session, a Class game (`game`), or one
 * Student (`student`, with the game it is written from, if any). */
export const messagePath = (sessionId: string, to: { game?: string; student?: string } = {}) => {
  const params = new URLSearchParams();
  if (to.game) params.set("spill", to.game);
  if (to.student) params.set("student", to.student);
  const query = params.toString();
  return `${classSessionPath(sessionId)}/melding${query ? `?${query}` : ""}`;
};

/** «Meldinger» (Story 7.10): the Messages a Class session was sent, for its staff. */
export const sentMessagesPath = (sessionId: string) => `${classSessionPath(sessionId)}/meldinger`;

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

export function homeOf(user: RoleHolder): Home {
  if (isStaff(user)) return "lecturerHome";
  if (isAdmin(user)) return "adminArea";
  return "home";
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
