import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { CrossInstitutionPage } from "@/modules/reports/cross-institution-page";

export const metadata: Metadata = { title: nb.crossInstitution.title };

/** «Tverrinstitusjonell statistikk» (Story 14.7, cut list): the stored aggregates by Institution. */
export default function TverrinstitusjonellStatistikkRoute() {
  return <CrossInstitutionPage />;
}
