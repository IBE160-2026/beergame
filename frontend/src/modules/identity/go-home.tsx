"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useMe } from "./api";
import { HOME_PATH, homeOf } from "./homes";

/**
 * `/`: a logged-in User goes on to their own home (Story 3.3). A visitor who is not logged in
 * sees an empty page until the Landing (Story 3.13).
 */
export function GoHome() {
  const router = useRouter();
  const user = useMe().data;
  useEffect(() => {
    if (user) router.replace(HOME_PATH[homeOf(user)]);
  }, [user, router]);
  return <main />;
}
