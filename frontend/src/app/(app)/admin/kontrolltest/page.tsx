import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { ControlTestsPage } from "@/modules/admin/control-tests-page";

export const metadata: Metadata = { title: nb.admin.controlTests.title };

export default function AdminControlTestsPage() {
  return <ControlTestsPage />;
}
