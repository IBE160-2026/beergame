"use client";

import { nb } from "@/copy/nb";
import { SCORING_PATH } from "@/modules/identity/homes";
import { PageLink } from "@/modules/identity/page-shell";

import { useMyScoring } from "./scoring-api";

/**
 * «Sensur av Kontrolltest» on the User's own home (Story 12.9, FR-82): shown only while the api
 * lists a Control test they are a named scorer of. Nothing while it loads or when it fails: the
 * home is never held up by it.
 */
export function ScoringLink() {
  const found = useMyScoring();
  if (!found.data || found.data.tests.length === 0) return null;
  return <PageLink href={SCORING_PATH}>{nb.scoring.homeLink}</PageLink>;
}
