import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { ConnectionLine } from "@/components/connection-notice";
import { nb } from "@/copy/nb";
import { InvitationPage } from "@/modules/identity/invitation-page";

const copy = nb.auth.invitation;

export const metadata: Metadata = {
  title: copy.pageTitle,
  // The link carries a secret in its fragment; no page it leads to needs a referrer.
  referrer: "no-referrer",
};

/** «Du er invitert» (Story 3.8): the page an Invitation mail links to, `/invitasjon#<token>`. The
 * token is read in the browser, so the page stays static. */
export default function InvitasjonPage() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="page-frame px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <ConnectionLine />
        <div className="max-w-sm">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <InvitationPage />
        </div>
      </main>
    </div>
  );
}
