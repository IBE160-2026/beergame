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
