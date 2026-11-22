"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { adaptedPreviewPath, classPath, classSessionPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";
import { useClassSession } from "@/modules/sessions/api";

import { type AdaptedPreview, type AdaptedPreviewItem, adaptedPreviewKey, useAdaptedPreview } from "./api";

const copy = nb.tests.adaptedPreview;
const LINE = "text-body-phone lg:text-body";

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * «Tilpassede oppgaver» (Story 11.9, FR-53, UX-DR70): each Adapted item template of the version
 * the Class session pins, filled by the server's code from a static sample Student's game and
 * labelled «Demodata», with the Adapted total weight from «Spørsmål og vekter» and each item's
 * share of it. A draft version carries the block's draft notice (issue #16). For the Class's
 * staff; anyone else sees the permission-denied page (FR-5).
 */
export function AdaptedPreviewPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        ID.test(sessionId) ? (
          <PreviewView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function PreviewView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useAdaptedPreview(sessionId);
  // The crumbs name the Class; the preview itself never waits on it.
  const session = useClassSession(sessionId);
  const { phase, retry } = usePageState(found, adaptedPreviewKey(sessionId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  const item = session.data;
  const crumbs = item
    ? ([
        { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
        { label: item.class_name, href: classPath(item.class_id) },
        { label: nb.sessions.crumb, href: classSessionPath(sessionId) },
        { label: copy.crumb, href: adaptedPreviewPath(sessionId) },
      ] as const)
    : undefined;
  return (
    <PageShell
      user={user}
      title={data ? copy.title : undefined}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 4, columns: 1 }}
    >
      {data ? <PreviewBody preview={data} /> : null}
    </PageShell>
  );
}

function PreviewBody({ preview }: { preview: AdaptedPreview }) {
  return (
    <div className="mt-2 flex max-w-[40rem] flex-col" data-adapted-preview="">
      <p className={`${LINE} text-ink-secondary`}>{copy.lead}</p>
      <p className={`${LINE} mt-2 text-ink-secondary`}>{copy.sample}</p>
      <p className={`${LINE} mt-2 text-ink-secondary`}>{copy.wordings}</p>
      {preview.draft ? (
        <p data-adapted-preview-draft="" className={`${LINE} mt-2 font-semibold text-ink`}>
          {nb.tests.questionSet.draft}
        </p>
      ) : null}
      <p data-adapted-preview-total="" className={`${LINE} mt-6 font-semibold text-ink tabular-nums`}>
        {copy.total(preview.adapted_weight)}
      </p>
      <ol className="mt-2 flex flex-col border-t border-hairline">
        {preview.items.map((entry, i) => (
          <PreviewItem key={entry.id} entry={entry} number={i + 1} />
        ))}
      </ol>
    </div>
  );
}

/** One template: «Oppgave n», where it reads from and its Vekt, then the filled text with its
 * «Demodata» caption (UX-DR70), or a line saying the sample has no such fact. */
function PreviewItem({ entry, number }: { entry: AdaptedPreviewItem; number: number }) {
  return (
    <li className="border-b border-hairline py-4" data-adapted-item={entry.id}>
      <h2 className={`${LINE} font-semibold text-ink`}>{copy.item(number)}</h2>
      <p className="mt-1 text-caption text-ink-secondary tabular-nums">
        {copy.sources[entry.source] ?? entry.source} · {copy.weightText(entry.weight)}
      </p>
      {entry.text ? (
        <figure className="mt-3">
          <blockquote className={`${LINE} border-l-2 border-axis pl-4 text-ink [overflow-wrap:anywhere]`}>
            <p>{entry.text}</p>
          </blockquote>
          <figcaption className="mt-2 text-right text-caption text-ink-muted">{nb.terms.demoData}</figcaption>
        </figure>
      ) : (
        <p className={`${LINE} mt-3 text-ink-secondary`}>{copy.noFact}</p>
      )}
    </li>
  );
}
