import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { ConnectionLine } from "@/components/connection-notice";
import { nb } from "@/copy/nb";
import { ForgotForm } from "@/modules/identity/forgot-form";

const copy = nb.auth.forgot;

export const metadata: Metadata = {
  title: copy.pageTitle,
};

/** «Glemt passord» (Story 3.6): ask for a reset link by e-mail. The same shell as «Logg inn». */
export default function GlemtPassordPage() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="page-frame px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <ConnectionLine />
        <div className="max-w-sm">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <ForgotForm />
        </div>
      </main>
    </div>
  );
}
