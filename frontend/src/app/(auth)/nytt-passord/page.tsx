import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { ConnectionLine } from "@/components/connection-notice";
import { nb } from "@/copy/nb";
import { ResetPassword } from "@/modules/identity/reset-password";

const copy = nb.auth.reset;

export const metadata: Metadata = {
  title: copy.pageTitle,
  // The link carries a secret in its fragment; no page it leads to needs a referrer.
  referrer: "no-referrer",
};

/** «Nytt passord» (Story 3.6): the page a reset mail links to, `/nytt-passord#<token>`. The token
 * is read in the browser, so the page stays static. */
export default function NyttPassordPage() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <ConnectionLine />
        <div className="max-w-sm">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <ResetPassword />
        </div>
      </main>
    </div>
  );
}
