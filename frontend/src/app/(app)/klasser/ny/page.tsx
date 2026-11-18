import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { NewClassPage } from "@/modules/classes/new-class-page";

export const metadata: Metadata = { title: nb.classes.create.title };

export default function LagKlassePage() {
  return <NewClassPage />;
}
