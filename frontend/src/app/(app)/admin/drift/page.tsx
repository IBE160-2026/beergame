import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { OperationsListPage } from "@/modules/ops/operations-page";

export const metadata: Metadata = { title: nb.admin.operations.title };

/** «Drift»: the Class sessions with their errors of the last 24 hours (Story 15.8). */
export default function AdminOperationsPage() {
  return <OperationsListPage />;
}
