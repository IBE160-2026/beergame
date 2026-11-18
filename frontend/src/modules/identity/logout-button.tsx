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
    // The error line hangs under the button in the space above the content, so it does not widen
    // the header and push the name and «Logg ut» onto a new row at phone width.
    <div className="relative">
      <Button variant="secondary" unavailable={logout.isPending} onClick={onClick}>
        {copy.logout}
      </Button>
      <ActionError
        message={logout.errorMessage}
        className="absolute top-full right-0 mt-1 w-max max-w-[calc(100vw-2*var(--spacing-gutter-phone))] text-right"
      />
    </div>
  );
}
