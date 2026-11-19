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

/** «Lag Klasse» (Story 4.1). */
export const NEW_CLASS_PATH = "/klasser/ny";

/** A Class's own page (Story 4.1). */
export const classPath = (id: string) => `/klasser/${encodeURIComponent(id)}`;

/** «Faglærere og assistenter» of a Class (Story 4.9). */
export const classStaffPath = (id: string) => `${classPath(id)}/faglaerere`;

/** A Class session's Klasseøkt screen (Story 5.1). */
export const classSessionPath = (id: string) => `/klasseokter/${encodeURIComponent(id)}`;

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
