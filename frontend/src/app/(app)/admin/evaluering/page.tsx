import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { EvaluationPage } from "@/modules/admin/evaluation-page";

export const metadata: Metadata = { title: nb.admin.evaluation.title };

export default function AdminEvaluationPage() {
  return <EvaluationPage />;
}
