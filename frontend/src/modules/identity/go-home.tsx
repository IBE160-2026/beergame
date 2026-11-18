"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { usePageState } from "@/lib/page-state";

import { meKey, useMe } from "./api";
import { HOME_PATH, homeOf } from "./homes";
import { PageShell } from "./page-shell";

/**
 * `/`: a logged-in User goes on to their own home (Story 3.3). A visitor who is not logged in
 * sees an empty page until the Landing (Story 3.13).
 */
export function GoHome() {
  const router = useRouter();
  const me = useMe();
  const { phase, retry } = usePageState(me, meKey);
  const user = me.data;
  useEffect(() => {
    if (user) router.replace(HOME_PATH[homeOf(user)]);
  }, [user, router]);
  if (user === null) return <main />;
  // Loading, on the way home, or failed: the shell says which (Story 3.4).
  return <PageShell phase={phase === "ready" ? "loading" : phase} onRetry={retry} />;
}
