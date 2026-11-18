import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { AuditPage } from "@/modules/admin/audit-page";

export const metadata: Metadata = { title: nb.admin.audit.title };

export default function AdminAuditPage() {
  return <AuditPage />;
}
