"use client";

import { useId, useState } from "react";

import { LINK_BUTTON } from "@/components/link";
import { nb } from "@/copy/nb";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { GuardedPage } from "@/modules/identity/home-page";
import { PageShell } from "@/modules/identity/page-shell";
import { enrolledSessionsKey, useEnrolledSessions } from "@/modules/sessions/api";

import { type MyDataCategory, myDataKey, useMyData } from "./api";
import { fieldLabel, fieldValue, itemHeading } from "./my-data";
import { ReportDownload } from "./report-download";

const copy = nb.myData;
const LINE = "text-body-phone text-ink lg:text-body";
const QUIET = "text-body-phone text-ink-secondary lg:text-body";
const H2 = "text-headline text-ink";

/**
 * «Mine data» (Story 15.1, FR-75, UX-DR67, EXPERIENCE.md → Mine data): everything the product
 * stores about the User, for the right of access. «Last ned Studentrapport» is at the top, the
 * Story 13.7 block for each Klasseøkt with a game (before the Testfrist it says when it opens).
 * Then one row per category, its name and how many rows it holds, with «Vis»: the stored rows,
 * each with its Class and Klasseøkt, its time and its fields, or «Ingenting er lagret.». Only the
 * User's own data: the api reads by the caller's id.
 */
export function MyDataPage() {
  return (
    <GuardedPage page="any">
      {(user, updatedAt) => <MyData user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function MyData({ user, updatedAt }: { user: SessionUser; updatedAt: number }) {
  const data = useMyData();
  const sessions = useEnrolledSessions();
  const dataState = usePageState(data, myDataKey);
  const sessionState = usePageState(sessions, enrolledSessionsKey);
  // The page stands on its data; the report block alone waits for the Klasseøkter, and their
  // failure shows in that block only.
  const phase = dataState.phase;
  const retry = dataState.retry;
  const withGame = (sessions.data?.items ?? []).filter((session) => session.game !== null);
  return (
    <PageShell
      user={user}
      title={copy.title}
      phase={phase}
      onRetry={retry}
      updatedAt={Math.max(updatedAt, data.dataUpdatedAt)}
    >
      <p className={`mt-4 max-w-prose ${QUIET}`}>{copy.intro}</p>
      <section aria-labelledby="mine-data-report" className="mt-8 max-w-prose">
        <h2 id="mine-data-report" className={H2}>
          {copy.reportHeading}
        </h2>
        {sessionState.phase === "failed" ? (
          <p role="alert" className={`mt-2 ${LINE}`}>
            {nb.system.pageError}
          </p>
        ) : sessions.data && withGame.length === 0 ? (
          <p className={`mt-2 ${QUIET}`}>{copy.reportNone}</p>
        ) : null}
        {withGame.map((session) => (
          <div key={session.id} className="mt-4" data-report-session={session.id}>
            {withGame.length > 1 ? (
              <h3 className={`${LINE} font-semibold`}>{copy.context(session.class_name, session.number)}</h3>
            ) : null}
            <ReportDownload sessionId={session.id} />
          </div>
        ))}
      </section>
      <section aria-labelledby="mine-data-categories" className="mt-10 max-w-prose">
        <h2 id="mine-data-categories" className={H2}>
          {copy.categoriesHeading}
        </h2>
        <ul className="mt-2 divide-y divide-hairline border-y border-hairline">
          {(data.data?.categories ?? []).map((category) => (
            <CategoryRow key={category.key} category={category} />
          ))}
        </ul>
      </section>
    </PageShell>
  );
}

function CategoryRow({ category }: { category: MyDataCategory }) {
  const [open, setOpen] = useState(false);
  const ids = useId();
  const name = copy.categories[category.key] ?? category.key;
  const nameId = `${ids}-name`;
  const panelId = `${ids}-panel`;
  return (
    <li className="py-2" data-category={category.key}>
      <div className="flex flex-wrap items-center justify-between gap-x-4">
        <p className={LINE}>
          <span id={nameId} className="font-semibold">
            {name}
          </span>{" "}
          <span className="text-ink-secondary">{copy.count(category.items.length)}</span>
        </p>
        <button
          type="button"
          className={LINK_BUTTON}
          aria-expanded={open}
          aria-controls={panelId}
          aria-describedby={nameId}
          onClick={() => setOpen((was) => !was)}
        >
          {open ? copy.hide : copy.show}
        </button>
      </div>
      {open ? (
        <div id={panelId} className="mt-2 pb-2">
          {category.items.length === 0 ? (
            <p className={QUIET}>{copy.empty}</p>
          ) : (
            <ol className="flex flex-col gap-3">
              {category.items.map((item, i) => {
                const heading = itemHeading(item);
                return (
                  <li key={i} className="border-l-2 border-hairline pl-3">
                    <p className={`${LINE} font-semibold [overflow-wrap:anywhere]`}>
                      {heading.kind}
                      {heading.context ? <span className="font-normal text-ink-secondary"> · {heading.context}</span> : null}
                    </p>
                    {item.at ? <p className={QUIET}>{copy.stored(fieldValue({ key: "at", kind: "datetime", value: item.at }))}</p> : null}
                    {item.fields.length > 0 ? (
                      <dl className="mt-1 grid grid-cols-1 gap-x-4 sm:grid-cols-[minmax(8rem,auto)_1fr]">
                        {item.fields.map((field) => (
                          <div key={field.key} className="contents">
                            <dt className={QUIET}>{fieldLabel(field.key)}</dt>
                            <dd className={`${LINE} whitespace-pre-line [overflow-wrap:anywhere]`}>{fieldValue(field)}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      ) : null}
    </li>
  );
}
