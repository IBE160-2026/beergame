"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/button";
import { nb } from "@/copy/nb";

import { useLogout } from "./api";

const copy = nb.auth.session;

/** «Logg ut»: clears the session cookie, empties the query cache and returns to «Logg inn». */
export function LogoutButton() {
  const router = useRouter();
  const logout = useLogout();
  const [failed, setFailed] = useState(false);

  function onClick() {
    if (logout.isPending) return;
    setFailed(false);
    logout.mutate(undefined, {
      onSuccess: () => router.push("/logg-inn"),
      onError: () => setFailed(true),
    });
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button variant="secondary" unavailable={logout.isPending} onClick={onClick}>
        {copy.logout}
      </Button>
      {failed ? (
        <p role="alert" className="text-body-phone text-restordre">
          {copy.logoutFailed}
        </p>
      ) : null}
    </div>
  );
}
