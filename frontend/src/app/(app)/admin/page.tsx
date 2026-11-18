import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { HomePage } from "@/modules/identity/home-page";

export const metadata: Metadata = { title: nb.homes.adminArea };

export default function AdminAreaPage() {
  return <HomePage page="adminArea" />;
}
