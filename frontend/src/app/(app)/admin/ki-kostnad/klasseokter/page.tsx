import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AiCostPage } from "@/modules/admin/ai-cost-page";

export const metadata: Metadata = { title: nb.admin.aiCost.costs.title };

/** «KI-kostnad per Klasseøkt» (Story 15.6). */
export default function AdminAiCostsPage() {
  return <AiCostPage />;
}
