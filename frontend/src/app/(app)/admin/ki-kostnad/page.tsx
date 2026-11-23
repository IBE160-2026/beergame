import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AiModelsPage } from "@/modules/admin/ai-models-page";
import { parseDay } from "@/modules/admin/daily-spend";

export const metadata: Metadata = { title: nb.admin.aiCost.title };

/** «KI-kostnad»; `?dag=2026-11-19` opens the AI spend of that day (Story 15.7). */
export default async function AdminAiCostPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { dag } = await searchParams;
  return <AiModelsPage day={parseDay(typeof dag === "string" ? dag : undefined)} />;
}
