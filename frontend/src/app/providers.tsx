"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useEffect, useState } from "react";

import { isSessionExpired } from "@/lib/api/client";
import { errorCode } from "@/lib/api/mutation";
import { LOGIN_PATH, loginPath } from "@/lib/return-path";

/**
 * A request found the session ended (401 `session_expired`): go to «Logg inn» with «Du er logget
 * ut. …» and the way back to this page (UX-DR59, Story 3.4). A full load, so nothing of the old
 * session stays in memory.
 */
function onApiError(error: unknown) {
  if (!isSessionExpired(error) || window.location.pathname === LOGIN_PATH) return;
  const here = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  window.location.replace(loginPath(here, true));
}

/** The app shell's one TanStack Query client: all server state lives here (AD-10). */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => {
    const client: QueryClient = new QueryClient({
      queryCache: new QueryCache({ onError: onApiError }),
      mutationCache: new MutationCache({
        onError: (error) => {
          onApiError(error);
          // The Class was archived while its page was open (Story 4.10): every Class read is read
          // again, so the page turns read-only.
          if (errorCode(error) === "class_archived") {
            void client.invalidateQueries({ queryKey: ["classes"] });
            void client.invalidateQueries({ queryKey: ["class-sessions"] }); // Story 5.1
          }
        },
      }),
      defaultOptions: {
        // Reconnecting refetches every active query below, stale or not.
        queries: { staleTime: 30_000, refetchOnWindowFocus: false, refetchOnReconnect: false },
        // An action pressed offline fails at once and is never queued: nothing is sent on its
        // own when the connection returns (UX-DR59).
        mutations: { networkMode: "always", retry: false },
      },
    });
    return client;
  });

  // Back online: the page refreshes its data in place, without moving focus (UX-DR59, NFR-5).
  useEffect(() => {
    const refetch = () => void queryClient.refetchQueries({ type: "active" });
    window.addEventListener("online", refetch);
    return () => window.removeEventListener("online", refetch);
  }, [queryClient]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
