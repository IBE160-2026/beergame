"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { request } from "@/lib/api/mutation";
import type { components } from "@/lib/api/schema";

import { classReportKey } from "./class-report-api";

/** «Alle spill i plenum» (Story 14.6): Netto lager and Orders per Role and Week, by game number. */
export type Plenary = components["schemas"]["PlenaryOut"];
export type PlenaryRole = components["schemas"]["PlenaryRoleOut"];

/** Under the Klasserapport's key, so `session:<id>` reads it again as games move (`lib/api/topics.ts`). */
export const plenaryKey = (sessionId: string) => [...classReportKey(sessionId), "plenary"] as const;

/** `/api/class-sessions/{id}/plenary`, the page's only read: 403 `forbidden` for anyone who may
 * not see the Oversikt and for a Class session that does not exist. */
export function useClassPlenary(sessionId: string) {
  return useQuery({
    queryKey: plenaryKey(sessionId),
    queryFn: () =>
      request(() =>
        api.GET("/api/class-sessions/{session_id}/plenary", {
          params: { path: { session_id: sessionId } },
          cache: "no-store",
        }),
      ),
    retry: false,
  });
}
