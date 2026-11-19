"use client";

import { nb } from "@/copy/nb";

import { type InvitationSummary as Summary, useInvitationSummary } from "./api";

const copy = nb.classes.invitations;

/** The four counts in the order the Invitations travel. */
export const COUNTS = [
  ["sent", copy.sent],
  ["bounced", copy.bounced],
  ["accepted", copy.accepted],
  ["expired", copy.expired],
] as const satisfies readonly (readonly [keyof Summary, string])[];

/** Whether anything has happened to the Class's Invitations yet. */
export function hasActivity(summary: Summary): boolean {
  return COUNTS.some(([key]) => summary[key] > 0) || summary.bounces.length > 0;
}

/**
 * «Invitasjoner» on the Class page (Story 4.6, FR-8, NFR-10): how many Invitations were sent,
 * bounced, accepted and expired, as the api counts them, each a caption over its figure on one
 * hairline row (two by two on a phone). Under it, the Roster addresses the mail did not reach,
 * each with its status in text: «Kom ikke fram, permanent feil» or «… midlertidig feil». The
 * section shows once a mail has gone out (nothing while it loads, or before any sending).
 */
export function InvitationSummary({ classId }: { classId: string }) {
  const summary = useInvitationSummary(classId);
  if (summary.isPending) return null;
  const data = summary.data;
  if (data && !hasActivity(data)) return null;
  return (
    <section aria-labelledby="invitations-title" className="mt-10">
      <h2 id="invitations-title" className="text-headline text-ink">
        {copy.title}
      </h2>
      <div className="mt-4">
        {!data ? (
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {copy.failed}
          </p>
        ) : (
          <Counts data={data} />
        )}
      </div>
    </section>
  );
}

function Counts({ data }: { data: Summary }) {
  return (
    <>
      <dl className="grid max-w-2xl grid-cols-2 border-y border-hairline sm:grid-cols-4">
        {COUNTS.map(([key, label]) => (
          <div key={key} className="flex flex-col gap-1 py-3 pr-4">
            <dt className="text-caption text-ink-secondary">{label}</dt>
            <dd className="text-figure-total text-ink">{data[key]}</dd>
          </div>
        ))}
      </dl>
      {data.bounces.length > 0 ? (
        <div className="mt-8 max-w-2xl">
          <h3 className="text-label text-ink">{copy.bouncedTitle}</h3>
          <p className="mt-1 text-body-phone text-ink-secondary lg:text-body">{copy.bouncedLead}</p>
          <ul className="mt-3 border-t border-hairline">
            {data.bounces.map((item) => (
              <li
                key={item.email}
                className="flex flex-col gap-1 border-b border-hairline py-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4"
              >
                <span className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">{item.email}</span>
                <span className="text-body-phone text-ink-secondary lg:text-body sm:shrink-0">
                  {copy.bounceStatus(item.bounce_class)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </>
  );
}
