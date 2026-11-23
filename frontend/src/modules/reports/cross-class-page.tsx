"use client";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { crossClassPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import { type CompareRow, compareRows, measureName, nothingToCompare, sessionName, splitSessions } from "./cross-class";
import { type ComparedMeasure, type ComparedSession, type CrossClass, crossClassKey, useClassStatistics } from "./cross-class-api";
import { SECONDARY, Section, Table, TEXT, Toggled } from "./class-report-parts";

const copy = nb.crossClass;

/**
 * Tverrklasse-statistikk (Story 14.3, FR-65, UX-DR55, `09-alle-sider.png`): the Lecturer's own
 * Class sessions compared on the stored aggregates, «Samme mål, samme regnestykke.». Each measure
 * is a row of `aria-hidden` bars, one per Class session with an aggregate, the value printed and
 * read beside it, with «Vis som tabell» under it. A figure withheld because its group held fewer
 * than 10 Students, or not measured, is said in words and has no bar. Every number is the api's
 * (AD-10); anyone without the Lecturer role sees the permission-denied page.
 */
export function CrossClassPage() {
  return <GuardedPage page="lecturerHome">{(user, updatedAt) => <View user={user} updatedAt={updatedAt} />}</GuardedPage>;
}

function View({ user, updatedAt }: { user: SessionUser; updatedAt: number }) {
  const found = useClassStatistics();
  const { phase, retry } = usePageState(found, crossClassKey);
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  const crumbs = [
    { label: nb.homes.lecturerHome, href: HOME_PATH.lecturerHome },
    { label: copy.crumb, href: crossClassPath },
  ] as const;
  return (
    <PageShell
      user={user}
      title={copy.title}
      updatedAt={updatedAt}
      crumbs={crumbs}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      skeleton={{ rows: 6, columns: 2 }}
    >
      {data ? <Comparison data={data} /> : null}
    </PageShell>
  );
}

function Comparison({ data }: { data: CrossClass }) {
  if (nothingToCompare(data)) {
    return (
      <p className={`mt-2 ${TEXT}`} data-cross-class-empty="">
        {copy.empty}
      </p>
    );
  }
  const { ready, waiting } = splitSessions(data);
  return (
    <div className="mt-2 flex min-w-0 flex-col" data-cross-class="">
      <p className={`${TEXT} font-semibold`}>{copy.intro}</p>
      <p className={`mt-1 ${SECONDARY}`}>{copy.about}</p>
      {ready.length < 2 ? (
        <p className={`mt-4 ${TEXT}`} data-cross-class-none-ready="">
          {copy.noneReady}
        </p>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
          {data.measures.map((measure) => (
            <Measure key={measure.key} measure={measure} sessions={ready} />
          ))}
        </div>
      )}
      {waiting.length > 0 ? <Waiting sessions={waiting} /> : null}
    </div>
  );
}

function Measure({ measure, sessions }: { measure: ComparedMeasure; sessions: readonly ComparedSession[] }) {
  const name = measureName(measure.key);
  const rows = compareRows(measure, sessions);
  const slug = measure.key.replaceAll(".", "-");
  return (
    <Section title={name} name={slug}>
      <Toggled
        name={slug}
        chart={<CompareBars rows={rows} name={slug} />}
        table={
          <Table
            name={slug}
            caption={copy.tableCaption(name)}
            columns={[copy.sessionColumn, copy.valueColumn]}
            rows={rows.map((row) => ({ key: row.key, head: row.session, cells: [row.text] }))}
          />
        }
      />
    </Section>
  );
}

/** One bar per Class session, its value printed beside it; the words are read, the bars are not. */
function CompareBars({ rows, name }: { rows: readonly CompareRow[]; name: string }) {
  return (
    <ol className="mt-1" data-compare-bars={name}>
      {rows.map((row) => (
        <li
          key={row.key}
          className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 py-1 text-body-phone lg:grid-cols-[minmax(0,12rem)_minmax(0,1fr)_auto] lg:text-body"
          data-compare-row=""
        >
          <span className="sr-only">{row.reads}</span>
          <span aria-hidden="true" className="[overflow-wrap:anywhere]">
            {row.session}
          </span>
          <span aria-hidden="true" className="order-last col-span-2 flex h-3 min-w-0 lg:order-none lg:col-span-1">
            {row.share != null ? (
              /* Drawn as a top border, so the bar is no text background. */
              <span className="block h-0 border-t-[0.75rem] border-order-history" style={{ width: `${(row.share * 100).toFixed(2)}%` }} />
            ) : null}
          </span>
          <span
            aria-hidden="true"
            className={`text-right tabular-nums lining-nums ${row.share != null ? "font-semibold" : "text-ink-secondary"}`}
            data-compare-value=""
          >
            {row.text}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Waiting({ sessions }: { sessions: readonly ComparedSession[] }) {
  return (
    <section aria-labelledby="cross-class-waiting" className="mt-10" data-cross-class-waiting="">
      <h2 id="cross-class-waiting" className="text-headline text-ink">
        {copy.notReadyTitle}
      </h2>
      <p className={`mt-1 ${SECONDARY}`}>{copy.notReady}</p>
      <ul className="mt-2 max-w-2xl">
        {sessions.map((session) => (
          <li key={session.class_session_id} className={`border-b border-hairline py-1 ${TEXT}`}>
            {sessionName(session)}
            {session.archived ? <span className="text-ink-secondary">{` (${copy.archived})`}</span> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
