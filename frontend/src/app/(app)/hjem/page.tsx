import type { Metadata } from "next";

import { nb } from "@/copy/nb";
import { HomePage } from "@/modules/identity/home-page";
import { StudentHomeWithSeatChoice } from "@/modules/sessions/seat-choice-home";

export const metadata: Metadata = { title: nb.homes.home };

export default function StudentHomePage() {
  return (
    <HomePage page="home">
      <StudentHomeWithSeatChoice />
    </HomePage>
  );
}
