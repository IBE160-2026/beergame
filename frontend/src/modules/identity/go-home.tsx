"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useMe } from "./api";
import { HOME_PATH, homeOf } from "./homes";

/**
 * On `/`: a logged-in User goes on to their own home (Story 3.3). It renders nothing, so the
 * Landing (Story 3.13) shows at once for a visitor. A failed read leaves the visitor on the
 * Landing; an ended session goes to «Logg inn», as on every page (Story 3.4).
 */
export function GoHome() {
  const router = useRouter();
  const { data: user } = useMe();
  useEffect(() => {
    if (user) router.replace(HOME_PATH[homeOf(user)]);
  }, [user, router]);
  return null;
}
