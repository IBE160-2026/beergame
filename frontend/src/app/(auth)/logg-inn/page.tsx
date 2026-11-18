import type { Metadata } from "next";

import { AppHeader } from "@/components/app-header";
import { nb } from "@/copy/nb";
import { LoginForm } from "@/modules/identity/login-form";

const copy = nb.auth.login;

export const metadata: Metadata = {
  title: copy.pageTitle,
};

export default function LoggInnPage() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <div className="max-w-sm">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.lead}</p>
          <LoginForm />
        </div>
      </main>
    </div>
  );
}
