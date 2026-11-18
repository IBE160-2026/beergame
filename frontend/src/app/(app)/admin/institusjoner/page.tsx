import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { InstitutionsPage } from "@/modules/admin/institutions-page";

export const metadata: Metadata = { title: nb.admin.institutions.title };

export default function AdminInstitutionsPage() {
  return <InstitutionsPage />;
}
