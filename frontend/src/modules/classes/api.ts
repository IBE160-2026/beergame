"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

export type ClassListItem = components["schemas"]["ClassListItem"];
export type ClassDetail = components["schemas"]["ClassOut"];
export type InstitutionChoice = components["schemas"]["InstitutionChoice"];
export type NewClass = { name: string; institution_id: string | null; course_code: string | null };

/** The query key of the User's Classes (Story 4.1). */
export const classesKey = ["classes"] as const;
export const classKey = (id: string) => ["classes", "detail", id] as const;
export const classInstitutionsKey = ["classes", "institutions"] as const;

/** The Classes the User is staff of, by name: «Klassene dine». */
export function useClasses() {
  return useQuery({
    queryKey: classesKey,
    queryFn: () => request(() => api.GET("/api/classes")),
    retry: false,
  });
}

/** One Class. A Class the User may not read, or one that does not exist, fails with 403
 * `forbidden`: the page then shows the permission-denied state (FR-5). */
export function useClass(id: string) {
  return useQuery({
    queryKey: classKey(id),
    queryFn: () => request(() => api.GET("/api/classes/{class_id}", { params: { path: { class_id: id } } })),
    retry: false,
  });
}

export const enrolledClassesKey = ["classes", "enrolled"] as const;

/** The Classes the User is a Student in, by name (Story 4.5): what Hjem names. */
export function useEnrolledClasses() {
  return useQuery({
    queryKey: enrolledClassesKey,
    queryFn: () => request(() => api.GET("/api/classes/enrolled")),
    retry: false,
  });
}

/** The Institutions a new Class may belong to, by name («Lag Klasse»). */
export function useClassInstitutions() {
  return useQuery({
    queryKey: classInstitutionsKey,
    queryFn: () => request(() => api.GET("/api/classes/institutions")),
    retry: false,
  });
}

/** Create a Class (Story 4.1). The list reads again, so the Lærerhjem shows it. The caller words
 * the refusals: each refused field goes beside its field. */
export function useCreateClass() {
  const queryClient = useQueryClient();
  return useMutation<ClassDetail, unknown, NewClass>({
    mutationFn: (body) => request(() => api.POST("/api/classes", { body })),
    networkMode: "always",
    retry: false,
    onSuccess: (created) => {
      queryClient.setQueryData(classKey(created.id), created);
      void queryClient.invalidateQueries({ queryKey: classesKey, exact: true });
    },
  });
}

/** «Arkiver Klassen» (Story 4.10): the Class becomes read-only. Answers the archived Class. */
export function archiveClass(classId: string) {
  return request(() => api.POST("/api/classes/{class_id}/archive", { params: { path: { class_id: classId } } }));
}

// The staged Roster upload of a Class (Story 4.2, FR-7).

export type RosterUpload = components["schemas"]["RosterUploadOut"];
export type RosterStaging = components["schemas"]["RosterStagingOut"];

export const rosterUploadKey = (classId: string) => ["classes", "roster-upload", classId] as const;

/** The Class's staged upload; `upload` is null when there is none or it has expired. */
export function useRosterUpload(classId: string) {
  return useQuery({
    queryKey: rosterUploadKey(classId),
    queryFn: () =>
      request(() => api.GET("/api/classes/{class_id}/roster-upload", { params: { path: { class_id: classId } } })),
    retry: false,
  });
}

/** Send the file as the raw body; its name travels percent-encoded in `X-File-Name`. The file is
 * read into memory by the api and never stored. */
export function uploadRoster(classId: string, file: File) {
  return request(() =>
    api.POST("/api/classes/{class_id}/roster-upload", {
      params: { path: { class_id: classId }, header: { "X-File-Name": encodeURIComponent(file.name) } },
      body: file as unknown as string,
      bodySerializer: (body: unknown) => body as BodyInit,
      headers: { "Content-Type": "application/octet-stream" },
    }),
  );
}

/** Stage pasted addresses (Story 4.3): the api splits the text and evaluates each piece. */
export function pasteRoster(classId: string, text: string) {
  return request(() =>
    api.POST("/api/classes/{class_id}/roster-paste", {
      params: { path: { class_id: classId } },
      body: { text },
    }),
  );
}

export function chooseRosterColumn(classId: string, column: number) {
  return request(() =>
    api.PUT("/api/classes/{class_id}/roster-upload/column", {
      params: { path: { class_id: classId } },
      body: { column },
    }),
  );
}

export function deleteRosterUpload(classId: string) {
  return request(() =>
    api.DELETE("/api/classes/{class_id}/roster-upload", { params: { path: { class_id: classId } } }),
  );
}

// Sending Invitations to the Roster (Story 4.4, FR-8).

export type RosterSent = components["schemas"]["RosterSendOut"];

/** «Send N Invitasjoner»: the staged upload the page shows and the validity in whole days. */
export function sendRosterInvitations(classId: string, uploadId: string, validDays: number) {
  return request(() =>
    api.POST("/api/classes/{class_id}/invitations", {
      params: { path: { class_id: classId } },
      body: { upload_id: uploadId, valid_days: validDays },
    }),
  );
}

// What became of the Invitations (Story 4.6, FR-8).

export type InvitationSummary = components["schemas"]["InvitationSummaryOut"];

export const invitationSummaryKey = (classId: string) => ["classes", "invitations", classId] as const;

/** How often the counts are read again while the page is open: the mails leave `worker-batch`
 * after the send returns, and bounces arrive from the provider later still. */
export const INVITATION_SUMMARY_REFRESH_MS = 15_000;

/** The counts of sent, bounced, accepted and expired Invitations, computed by the api, and the
 * addresses the mail did not reach. Read again every 15 s while the tab is visible. */
export function useInvitationSummary(classId: string) {
  return useQuery({
    queryKey: invitationSummaryKey(classId),
    queryFn: () =>
      request(() => api.GET("/api/classes/{class_id}/invitations", { params: { path: { class_id: classId } } })),
    retry: false,
    refetchInterval: INVITATION_SUMMARY_REFRESH_MS,
  });
}

// Registration status and reminders (Story 4.7, FR-9).

export type Registrations = components["schemas"]["RegistrationsOut"];
export type Registration = components["schemas"]["RegistrationOut"];
export type RegistrationStatus = components["schemas"]["RegistrationStatus"];
export type RemindersSent = components["schemas"]["ReminderOut"];

export const registrationsKey = (classId: string) => ["classes", "registrations", classId] as const;

/** Every Roster address with its status, the totals and how many have not registered, read by
 * the api now. Read again every 15 s while the tab is visible, as the counts are. */
export function useRegistrations(classId: string) {
  return useQuery({
    queryKey: registrationsKey(classId),
    queryFn: () =>
      request(() => api.GET("/api/classes/{class_id}/registrations", { params: { path: { class_id: classId } } })),
    retry: false,
    refetchInterval: INVITATION_SUMMARY_REFRESH_MS,
  });
}

/** «Send påminnelse»: a new Invitation to every address that has not registered, or with
 * `entryId` to that one alone, valid for `validDays`. */
export function sendReminders(classId: string, validDays: number, entryId?: string) {
  return request(() =>
    api.POST("/api/classes/{class_id}/reminders", {
      params: { path: { class_id: classId } },
      body: entryId ? { valid_days: validDays, roster_entry_id: entryId } : { valid_days: validDays },
    }),
  );
}

// Manual registration and single addresses (Story 4.8, FR-7, FR-9).

export type UploadRow = { upload_id: string; row_number: number };
export type ManualRegistration = {
  email: string;
  name: string;
  roster_entry_id?: string;
  upload_row?: UploadRow;
};

/** «Legg til adresse»: one address on the Roster, not yet invited (or a removed one put back). */
export function addRosterEntry(classId: string, email: string) {
  return request(() =>
    api.POST("/api/classes/{class_id}/roster/entries", { params: { path: { class_id: classId } }, body: { email } }),
  );
}

/** «Registrer manuelt»: the Student is in the Class at once and gets a mail. */
export function registerManually(classId: string, body: ManualRegistration) {
  return request(() =>
    api.POST("/api/classes/{class_id}/roster/manual", { params: { path: { class_id: classId } }, body }),
  );
}

/** Take an address off the Roster. */
export function removeRosterEntry(classId: string, entryId: string) {
  return request(() =>
    api.DELETE("/api/classes/{class_id}/roster/entries/{entry_id}", {
      params: { path: { class_id: classId, entry_id: entryId } },
    }),
  );
}

// The Class's staff (Story 4.9, FR-10): «Faglærere og assistenter», for its Faglærere.

export type ClassStaff = components["schemas"]["StaffOut"];
export type StaffLecturer = components["schemas"]["StaffLecturer"];
export type StaffAssistant = components["schemas"]["StaffAssistant"];

export const classStaffKey = (classId: string) => ["classes", "staff", classId] as const;

/** The Class's Faglærere and Assistenter with their status. */
export function useClassStaff(classId: string) {
  return useQuery({
    queryKey: classStaffKey(classId),
    queryFn: () =>
      request(() => api.GET("/api/classes/{class_id}/staff", { params: { path: { class_id: classId } } })),
    retry: false,
  });
}

/** «Legg til Faglærer»: a User with the Lecturer role becomes co-owner. */
export function addClassLecturer(classId: string, email: string) {
  return request(() =>
    api.POST("/api/classes/{class_id}/staff/lecturers", { params: { path: { class_id: classId } }, body: { email } }),
  );
}

/** «Inviter Assistent»: an Invitation for this Class only. */
export function inviteClassAssistant(classId: string, email: string) {
  return request(() =>
    api.POST("/api/classes/{class_id}/staff/assistants", { params: { path: { class_id: classId } }, body: { email } }),
  );
}

/** Take a Faglærer or an Assistent off the Class. */
export function removeClassStaff(classId: string, userId: string) {
  return request(() =>
    api.DELETE("/api/classes/{class_id}/staff/{user_id}", {
      params: { path: { class_id: classId, user_id: userId } },
    }),
  );
}

/** Withdraw an Assistant Invitation that is not accepted. */
export function withdrawAssistantInvitation(classId: string, invitationId: string) {
  return request(() =>
    api.DELETE("/api/classes/{class_id}/staff/invitations/{invitation_id}", {
      params: { path: { class_id: classId, invitation_id: invitationId } },
    }),
  );
}
