import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { ScoringTestsPage } from "@/modules/assessment/scoring-pages";

export const metadata: Metadata = { title: nb.scoring.title };

/** «Sensur av Kontrolltest» (Story 12.9): the Control tests the User scores. */
export default function ScoringRoute() {
  return <ScoringTestsPage />;
}
