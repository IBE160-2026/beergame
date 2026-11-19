import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { LecturerHome } from "@/modules/classes/lecturer-home";
import { HomePage } from "@/modules/identity/home-page";

export const metadata: Metadata = { title: nb.homes.lecturerHome };

export default function LecturerHomePage() {
  return (
    <HomePage page="lecturerHome">
      <LecturerHome />
    </HomePage>
  );
}
