"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { Link } from "@/components/link";
import { classPath, classStaffPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { classKey, useClass } from "./api";
import { InvitationSummary } from "./invitation-summary";
import { OneFormAtATime } from "./one-form";
import { RegistrationStatus } from "./registration-status";
import { RosterEntryActions } from "./roster-entry-forms";
import { RosterUpload } from "./roster-upload";

/**
 * A Class's own page (Story 4.1): its name as the heading, then the course code and Institution,
 * and for its owner the Roster upload (Story 4.2) with how many addresses the Roster holds (Story
 * 4.4), what became of the Invitations (Story 4.6) and where each address stands, with reminders
 * (Story 4.7), single addresses and manual registration (Story 4.8), and the Lenke to «Faglærere og
 * assistenter» (Story 4.9). An Assistant lecturer reads the Roster's count, the Invitation counts
 * and the status list, with no action (Story 4.9). A Class the User is not staff of, one that does
 * not exist and an address that names no Class all show the permission-denied page (FR-5): the api
 * answers them alike.
 */
export function ClassPage({ classId }: { classId: string }) {
  // An address that is no Class id is never sent to the api: as a path it could name another
  // route (`/api/classes/institutions`) or be rewritten (`..`). It is refused as any other.
  const named = CLASS_ID.test(classId);
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <ClassView classId={classId} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

/** The shape of a Class id (a UUID). */
const CLASS_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function ClassView({ classId, user, updatedAt }: { classId: string; user: SessionUser; updatedAt: number }) {
  const found = useClass(classId);
  const { phase, retry } = usePageState(found, classKey(classId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const item = found.data;
  const crumbs = item
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: item.name, href: classPath(item.id) },
      ] as const)
    : undefined;
  const facts = item ? nb.classes.page.facts(item.course_code, item.institution_name) : "";
  return (
    <PageShell
      user={user}
      title={item?.name}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={item ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      <OneFormAtATime>
        {facts ? <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{facts}</p> : null}
        {item?.can_manage ? (
          <p className="mt-4">
            <Link href={classStaffPath(item.id)} standalone>
              {nb.classes.page.staff}
            </Link>
          </p>
        ) : null}
        {/* The Roster upload is the Faglærere's (the api's `classes.manage` policy). */}
        {item?.can_manage ? (
          <section aria-labelledby="roster-title" className="mt-10">
            <h2 id="roster-title" className="text-headline text-ink">
              {nb.classes.roster.title}
            </h2>
            <p className="mt-1 max-w-2xl text-body-phone text-ink-secondary lg:text-body">{nb.classes.roster.lead}</p>
            {item.roster_count > 0 ? (
              <p className="mt-2 text-body-phone text-ink lg:text-body">{nb.classes.roster.onRosterCount(item.roster_count)}</p>
            ) : null}
            <div className="mt-6">
              <RosterUpload classId={item.id} />
            </div>
            {/* One address at a time, and a Student registered by hand (Story 4.8). */}
            <div className="mt-8">
              <RosterEntryActions classId={item.id} />
            </div>
          </section>
        ) : null}
        {/* An Assistant lecturer reads the Roster and changes nothing (Story 4.9). */}
        {item && !item.can_manage ? (
          <section aria-labelledby="roster-title" className="mt-10">
            <h2 id="roster-title" className="text-headline text-ink">
              {nb.classes.roster.title}
            </h2>
            <p className="mt-1 max-w-2xl text-body-phone text-ink-secondary lg:text-body">
              {nb.classes.page.assistantLead}
            </p>
            <p className="mt-2 text-body-phone text-ink lg:text-body">
              {item.roster_count > 0 ? nb.classes.roster.onRosterCount(item.roster_count) : nb.classes.home.rosterCount(0)}
            </p>
          </section>
        ) : null}
        {/* What became of the Invitations (Story 4.6), once a mail has gone out. */}
        {item && item.roster_count > 0 ? <InvitationSummary classId={item.id} /> : null}
        {/* Where each address stands, and reminders (Story 4.7), once the Roster has addresses. */}
        {item && item.roster_count > 0 ? <RegistrationStatus classId={item.id} readOnly={!item.can_manage} /> : null}
      </OneFormAtATime>
    </PageShell>
  );
}
