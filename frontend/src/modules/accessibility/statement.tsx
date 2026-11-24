import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { Link } from "@/components/link";
import { nb } from "@/copy/nb";

const copy = nb.accessibility;

function Part({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="mt-10">
      <h2 id={id} className="text-headline text-ink">
        {title}
      </h2>
      <div className="mt-3 flex flex-col gap-3 text-body-phone text-ink lg:text-body">{children}</div>
    </section>
  );
}

function Items({ items }: { items: readonly string[] }) {
  return (
    <ul className="flex list-disc flex-col gap-2 pl-5">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * The accessibility statement (Story 15.13, NFR-6), public at `/tilgjengelighet`: scope, the
 * standard and status, the known deviations, what is not yet checked, how the pages were checked,
 * the contact route and the complaint route. One column of running text at a reading width.
 */
export function AccessibilityStatement() {
  return (
    <div className="min-h-dvh">
      <AppHeader />
      <main className="page-frame px-gutter-phone pt-10 pb-16 lg:px-margin-laptop lg:pt-16">
        <article className="max-w-prose break-words">
          <h1 className="text-title-phone text-ink lg:text-title-page">{copy.title}</h1>
          <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.updated}</p>
          <p className="mt-6 text-body-phone text-ink lg:text-body">{copy.lead}</p>
          <Part id="krav" title={copy.standard.title}>
            <p>{copy.standard.body}</p>
          </Part>
          <Part id="avvik" title={copy.deviations.title}>
            {copy.deviations.items.length > 0 ? <Items items={copy.deviations.items} /> : <p>{copy.deviations.none}</p>}
          </Part>
          <Part id="ikke-kontrollert" title={copy.notYet.title}>
            <Items items={copy.notYet.items} />
          </Part>
          <Part id="kontroll" title={copy.tested.title}>
            <p>{copy.tested.body}</p>
          </Part>
          <Part id="kontakt" title={copy.contact.title}>
            <p>{copy.contact.student}</p>
            <p>{copy.contact.others}</p>
            {/* Lenker on lines of their own, each a 44 px tap target. */}
            <p>
              <Link href={`mailto:${copy.contact.email}`} standalone className="[overflow-wrap:anywhere]">
                {copy.contact.email}
              </Link>
            </p>
            <p>{copy.contact.answer}</p>
            <p>{copy.contact.alternative}</p>
          </Part>
          <Part id="klage" title={copy.complaint.title}>
            <p>{copy.complaint.body}</p>
            <p>
              <Link href={copy.complaint.href} standalone>
                {copy.complaint.link}
              </Link>
            </p>
          </Part>
        </article>
      </main>
    </div>
  );
}
