"use client";

import { useEffect, useRef, useState } from "react";

import { nb } from "@/copy/nb";
import { EXPIRED_PARAM } from "@/lib/return-path";

/**
 * «Du er logget ut. Logg inn igjen for å fortsette.» (UX-DR59, UX-DR76), when «Logg inn» was
 * opened with `?utlopt=1`. The page opens with focus here, so it is read on focus; it is not also
 * a live region, so it is read once.
 */
export function SessionExpiredNote() {
  const ref = useRef<HTMLParagraphElement>(null);
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    setExpired(new URLSearchParams(window.location.search).get(EXPIRED_PARAM) === "1");
  }, []);
  useEffect(() => {
    if (expired) ref.current?.focus();
  }, [expired]);
  if (!expired) return null;
  return (
    <p ref={ref} tabIndex={-1} className="mt-6 border-y border-ink-muted py-2 text-body-phone text-ink lg:text-body">
      {nb.auth.login.sessionExpired}
    </p>
  );
}
