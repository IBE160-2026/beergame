import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { CrossClassPage } from "@/modules/reports/cross-class-page";

export const metadata: Metadata = { title: nb.crossClass.title };

/** Tverrklasse-statistikk (Story 14.3): the Lecturer's Class sessions compared on stored aggregates. */
export default function TverrklasseStatistikkRoute() {
  return <CrossClassPage />;
}
