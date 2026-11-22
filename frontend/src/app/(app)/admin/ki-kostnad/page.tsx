import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AiModelsPage } from "@/modules/admin/ai-models-page";

export const metadata: Metadata = { title: nb.admin.aiCost.title };

export default function AdminAiCostPage() {
  return <AiModelsPage />;
}
