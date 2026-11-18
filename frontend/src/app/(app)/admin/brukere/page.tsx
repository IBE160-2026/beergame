import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { UsersPage } from "@/modules/admin/users-page";

export const metadata: Metadata = { title: nb.admin.users.title };

export default function AdminUsersPage() {
  return <UsersPage />;
}
