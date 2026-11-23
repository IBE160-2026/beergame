import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AccessibilityStatement } from "@/modules/accessibility/statement";

export const metadata: Metadata = {
  title: nb.accessibility.pageTitle,
};

/** `/tilgjengelighet`: the accessibility statement (Story 15.13, NFR-6), public, linked from the
 * footer of every page. */
export default function TilgjengelighetPage() {
  return <AccessibilityStatement />;
}
