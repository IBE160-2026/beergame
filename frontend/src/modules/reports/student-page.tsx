"use client";

import { useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classPath, classSessionPath, HOME_PATH, studentPagePath } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { StaffAssessmentBlock } from "@/modules/assessment/staff-block";

import { AdjustmentBlock } from "./adjustment-block";
import { type StudentPage, studentPageKey, useStudentPage } from "./api";
import { DeadlineBlock } from "./deadline-block";

/** The Studentside's in-place forms: one open at a time (EXPERIENCE.md → Studentside, «One
 * panel»); opening another closes the first and keeps nothing. */
type Editing = "adjustment" | "deadline" | null;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Studentside (Story 8.9, UX-DR53, EXPERIENCE.md → Studentside): one Student of a Class
 * session, as a page of blocks for the staff of its Class: «Tilrettelegging» and «Frister» (Story
 * 11.13) for its Lecturers only (`can_manage`), and «KI-vurdering» (Story 12.5) for its Lecturers
 * and Assistant lecturers; Story 13.2 adds its own blocks here. Reached from the Student's name on
 * Spillinnsikt and on the Klasseøkt's list of AI assessments. Anyone else sees the
 * permission-denied page (FR-5, AD-12).
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
  const [editing, setEditing] = useState<Editing>(null);
  const toggle = (block: Exclude<Editing, null>) => (open: boolean) =>
    setEditing((now) => (open ? block : now === block ? null : now));
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
      {data ? (
        <>
          {data.can_manage ? (
            <AdjustmentBlock data={data} open={editing === "adjustment"} onOpenChange={toggle("adjustment")} />
          ) : null}
          {data.can_manage && data.deadlines ? (
            <DeadlineBlock
              data={{ ...data, deadlines: data.deadlines }}
              open={editing === "deadline"}
              onOpenChange={toggle("deadline")}
            />
          ) : null}
          <StaffAssessmentBlock sessionId={sessionId} userId={userId} />
        </>
      ) : null}
    </PageShell>
  );
}
