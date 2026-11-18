import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { ConnectionLine } from "@/components/connection-notice";
import { nb } from "@/copy/nb";
import { LoginForm } from "@/modules/identity/login-form";
import { SessionExpiredNote } from "@/modules/identity/session-expired-note";

const copy = nb.auth.login;

export const metadata: Metadata = {
  title: copy.pageTitle,
};

/** «Logg inn». `?neste=` is the page to return to after login, kept only when it is a path on
 * this site; `?utlopt=1` says the session ended (Story 3.4). Both are read in the browser, so the
 * page stays static and its form works before hydration. */
export default function LoggInnPage() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <ConnectionLine />
        <div className="max-w-sm">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <SessionExpiredNote />
          <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <LoginForm />
        </div>
      </main>
    </div>
  );
}
