"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

/** The areas of the Class page that open forms in place: the invalid rows of an upload and the
 * «Legg til adresse» / «Registrer manuelt» Lenker under «Klasseliste», the status list, and
 * «Arkiver Klassen» (Story 4.10). */
export type FormArea = "invalid-rows" | "entries" | "status" | "archive";

type Claim = { area: FormArea; n: number } | null;

const OpenForm = createContext<{ claim: Claim; take: (area: FormArea) => void }>({
  claim: null,
  take: () => {},
});

/**
 * One in-place form on the Class page at a time (Story 4.8): an area that opens a form takes the
 * page, and every other area closes its form and clears its result line. Without this provider
 * (a component rendered alone) an area only governs its own forms.
 */
export function OneFormAtATime({ children }: { children: ReactNode }) {
  const [claim, setClaim] = useState<Claim>(null);
  const take = useCallback((area: FormArea) => setClaim((prev) => ({ area, n: (prev?.n ?? 0) + 1 })), []);
  const value = useMemo(() => ({ claim, take }), [claim, take]);
  return <OpenForm.Provider value={value}>{children}</OpenForm.Provider>;
}

/** For one area: `release` runs when another area opens a form; call the returned function when
 * this area opens one. */
export function useFormArea(area: FormArea, release: () => void): () => void {
  const { claim, take } = useContext(OpenForm);
  const latest = useRef(release);
  useEffect(() => {
    latest.current = release;
  });
  useEffect(() => {
    if (claim && claim.area !== area) latest.current();
  }, [claim, area]);
  return useCallback(() => take(area), [take, area]);
}
