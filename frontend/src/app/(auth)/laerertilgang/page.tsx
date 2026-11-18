import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { ConnectionLine } from "@/components/connection-notice";
import { nb } from "@/copy/nb";
import { AccessRequestForm } from "@/modules/access-request/request-form";

const copy = nb.accessRequest;

export const metadata: Metadata = {
  title: copy.pageTitle,
};

/** «Be om lærertilgang» (Story 3.13): the Landing's short public form. The same shell as
 * «Logg inn»; no account is created, the Admin answers by e-mail. */
export default function LaerertilgangPage() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <ConnectionLine />
        <div className="max-w-sm">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <AccessRequestForm />
        </div>
      </main>
    </div>
  );
}
