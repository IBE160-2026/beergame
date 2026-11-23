"use client";

import { useState } from "react";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classPath, classSessionPath, HOME_PATH, studentPagePath } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { AdjustmentBlock } from "./adjustment-block";
import { type StudentPage, studentRecordKey, useStudentPage, useStudentRecord } from "./api";
import { CompletionBlock } from "./completion-block";
import { DeadlineBlock } from "./deadline-block";
import { RecordBlocks } from "./record-blocks";
import type { StudentRecord } from "./record";

/** The Studentside's in-place forms: one open at a time (EXPERIENCE.md → Studentside, «One
 * panel»); opening another closes the first and keeps nothing. Story 13.3: the correction form
 * of one step of «Fullføring», `correct:<step>`. */
type Editing = "adjustment" | "deadline" | `correct:${string}` | null;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The Studentside (Story 8.9, UX-DR53, EXPERIENCE.md → Studentside): one Student of a Class
 * session, as a page of blocks for the staff of its Class (Story 13.2, FR-63): «Fullføring», the
 * record blocks and «KI-vurdering» with the Student's flags (Story 12.5) for its Lecturers and
 * Assistant lecturers, then «Tilrettelegging» and «Frister» (Story 11.13) for its Lecturers only
 * (`can_manage`). Reached from the Student's name on Spillinnsikt, on the Klasseøkt's list of AI
 * assessments and on the Roster. Anyone else sees the permission-denied page, which never says
 * whether the Student exists (FR-5, AD-12).
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
  const found = useStudentRecord(sessionId, userId);
  const data: StudentRecord | undefined = found.data;
  // «Tilrettelegging» and «Frister» are the Lecturers' (`getStudentPage`); an Assistant lecturer
  // never asks for them.
  const page = useStudentPage(sessionId, userId, data?.can_manage === true);
  const [editing, setEditing] = useState<Editing>(null);
  const toggle = (block: Exclude<Editing, null>) => (open: boolean) =>
    setEditing((now) => (open ? block : now === block ? null : now));
  const { phase, retry } = usePageState(found, studentRecordKey(sessionId, userId));
  const managed: StudentPage | undefined = data?.can_manage ? page.data : undefined;
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  if (found.error instanceof ApiRequestError && found.error.code === "data_deleted") {
    // Story 15.3 (FR-77): the Class session's Student data is deleted; the page says so.
    return (
      <PageShell user={user} title={nb.reports.studentPage.deletedTitle} updatedAt={updatedAt}>
        <div className="mt-4 flex flex-col items-start gap-3">
          <p className="max-w-prose text-body-phone text-ink lg:text-body">{nb.reports.studentPage.deleted}</p>
          <Link href={classSessionPath(sessionId)} standalone>
            {nb.reports.studentPage.toSession}
          </Link>
        </div>
      </PageShell>
    );
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
      skeleton={{ rows: 6, columns: 1 }}
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
          <CompletionBlock
            record={data}
            editing={editing?.startsWith("correct:") ? editing.slice("correct:".length) : null}
            onEditingChange={(step) =>
              setEditing((now) => (step ? `correct:${step}` : now?.startsWith("correct:") ? null : now))
            }
          />
          <RecordBlocks record={data} />
          {managed ? (
            <>
              <AdjustmentBlock data={managed} open={editing === "adjustment"} onOpenChange={toggle("adjustment")} />
              {managed.deadlines ? (
                <DeadlineBlock
                  data={{ ...managed, deadlines: managed.deadlines }}
                  open={editing === "deadline"}
                  onOpenChange={toggle("deadline")}
                />
              ) : null}
            </>
          ) : null}
        </>
      ) : null}
    </PageShell>
  );
}
