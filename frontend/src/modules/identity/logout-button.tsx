"use client";

import { useRouter } from "next/navigation";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";

import { useLogout } from "./api";

const copy = nb.auth.session;

/** «Logg ut»: clears the session cookie, empties the query cache and returns to «Logg inn». A
 * failure shows inline beside the button; the button stays active and keeps focus (Story 3.4). */
export function LogoutButton() {
  const router = useRouter();
  const logout = useLogout();

  function onClick() {
    if (logout.isPending) return;
    logout.mutate(undefined, { onSuccess: () => router.push("/logg-inn") });
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button variant="secondary" unavailable={logout.isPending} onClick={onClick}>
        {copy.logout}
      </Button>
      <ActionError message={logout.errorMessage} />
    </div>
  );
}
