import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { MyDataPage } from "@/modules/reports/my-data-page";

export const metadata: Metadata = { title: nb.myData.title };

/** «Mine data» (Story 15.1, FR-75): the User's own stored data, from Hjem. */
export default function Page() {
  return <MyDataPage />;
}
