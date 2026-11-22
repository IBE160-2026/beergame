"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classPath, classSessionPath, HOME_PATH, studentPagePath } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { AdjustmentBlock } from "./adjustment-block";
import { type StudentPage, studentPageKey, useStudentPage } from "./api";

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Studentside (Story 8.9, UX-DR53, EXPERIENCE.md → Studentside): one Student of a Class
 * session, as a page of blocks for the Lecturers of its Class. For now it holds the block
 * «Tilrettelegging» only; Story 13.2 adds its own blocks here. Reached from the Student's name on
 * Spillinnsikt. Anyone else, an Assistant lecturer included, sees the permission-denied page (FR-5,
 * AD-12).
 */
export function StudentPageView({ sessionId, userId }: { sessionId: string; userId: string }) {
  const named = ID.test(sessionId) && ID.test(userId);
  const [session, student] = [sessionId.toLowerCase(), userId.toLowerCase()];
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        named ? (
          <StudentPageBody sessionId={session} userId={student} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function StudentPageBody({
  sessionId,
  userId,
  user,
  updatedAt,
}: {
  sessionId: string;
  userId: string;
  user: SessionUser;
  updatedAt: number;
}) {
  const found = useStudentPage(sessionId, userId);
  const { phase, retry } = usePageState(found, studentPageKey(sessionId, userId));
  const data: StudentPage | undefined = found.data;
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const crumbs = data
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: data.class_name, href: classPath(data.class_id) },
        { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
        { label: data.name, href: studentPagePath(sessionId, userId) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={data?.name}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 3, columns: 1 }}
      header={
        data ? (
          <header className="flex flex-col gap-1">
            <h1 className="text-title-phone text-ink [overflow-wrap:anywhere] lg:text-title-page">{data.name}</h1>
            <p className="text-body-phone text-ink-secondary lg:text-body">
              {nb.reports.studentPage.session(data.session_number)}
            </p>
          </header>
        ) : undefined
      }
    >
      {data ? <AdjustmentBlock data={data} /> : null}
    </PageShell>
  );
}
