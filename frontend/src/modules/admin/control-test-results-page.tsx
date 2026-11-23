"use client";

import { Link } from "@/components/link";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";
import { usePageState } from "@/lib/page-state";
import {
  aiCell,
  compressionText,
  humanCell,
  offsetText,
  percentText,
  scorerHeading,
  statusLines,
} from "@/modules/assessment/results";
import { answerLabel, typeText } from "@/modules/assessment/scoring";
import { type ControlResults, controlResultsKey, useControlResults } from "@/modules/assessment/scoring-api";
import { GuardedPage } from "@/modules/identity/home-page";
import {
  ADMIN_CONTROL_TESTS_PATH,
  controlTestResultsPath,
  controlTestScorersPath,
  HOME_PATH,
} from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

const copy = nb.scoring.results;
const tests = nb.admin.controlTests;
const LINE = "text-body-phone lg:text-body";

const CRUMBS = [
  { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
  { label: tests.title, href: ADMIN_CONTROL_TESTS_PATH },
] as const;

/**
 * Admin-område → «Kontrolltest» → «Resultater» (Story 12.10, FR-82, FR-81, UX-DR57): the pinned
 * Scoring guide version and model config, whether the guide is checked or the numbers are
 * preliminary (and what is missing, in words), the five agreement measures as labelled numbers,
 * agreement by answer length, and every answer's human and AI steps side by side in an HTML table.
 * The api computes every measure (`analysis.agreement`); the page only formats them. Only an
 * Admin sees it.
 */
export function ControlTestResultsPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) => <ResultsBody sessionId={sessionId} user={user} updatedAt={updatedAt} />}
    </GuardedPage>
  );
}

function ResultsBody({
  sessionId,
  user,
  updatedAt,
}: {
  sessionId: string;
  user: Parameters<typeof PageShell>[0]["user"];
  updatedAt: number;
}) {
  const found = useControlResults(sessionId);
  const { phase, retry } = usePageState(found, controlResultsKey(sessionId));
  const notFound = found.error instanceof ApiRequestError && found.error.code === "not_found";
  const page = found.data;
  return (
    <PageShell
      user={user}
      title={page ? `${copy.title}: ${page.test.name}` : copy.title}
      updatedAt={updatedAt}
      phase={page || notFound ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
      crumbs={[
        ...CRUMBS,
        { label: nb.scoring.scorers.title, href: controlTestScorersPath(sessionId) },
        { label: copy.title, href: controlTestResultsPath(sessionId) },
      ]}
    >
      {notFound ? <p className={`${LINE} mt-2 text-ink`}>{copy.notFound}</p> : null}
      {page ? <ResultsView page={page} /> : null}
    </PageShell>
  );
}

function ResultsView({ page }: { page: ControlResults }) {
  const status = statusLines(page);
  return (
    <>
      <p className={`${LINE} mt-2 font-semibold text-ink`}>{tests.never}</p>
      <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.lead}</p>
      <dl className={`${LINE} mt-4 grid max-w-2xl grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-[auto_1fr]`}>
        <dt className="text-ink-secondary">{tests.list.guide}</dt>
        <dd className="text-ink">{tests.guide(page.scoring_guide.version, page.scoring_guide.edited, false)}</dd>
        <dt className="text-ink-secondary">{tests.list.config}</dt>
        <dd className="text-ink [overflow-wrap:anywhere]">
          {page.ai_config ? tests.config(page.ai_config.name, page.ai_config.model_version, false) : tests.list.configGone}
        </dd>
      </dl>
      <div role="status" data-results-status={page.complete && page.checked ? "checked" : "preliminary"} className="mt-4 max-w-2xl">
        {status.map((line, index) => (
          <p key={line} className={`${LINE} ${index === 0 ? "font-semibold" : ""} text-ink`}>
            {line}
          </p>
        ))}
      </div>
      {page.test.open && page.withheld ? (
        <p data-results-withheld="" className={`${LINE} mt-3 max-w-2xl border-y border-ink-muted py-2 text-ink`}>
          {copy.withheld}
        </p>
      ) : null}
      {page.measures ? <Measures page={page} /> : null}
      {page.test.open ? <SideBySide page={page} /> : null}
    </>
  );
}

function Measures({ page }: { page: ControlResults }) {
  const measures = page.measures!;
  const items = [
    { key: "exact", label: copy.measures.exact, value: percentText(measures.exact), help: copy.measures.exactHelp },
    {
      key: "within-one",
      label: copy.measures.withinOne,
      value: percentText(measures.within_one),
      help: copy.measures.withinOneHelp,
    },
    { key: "offset", label: copy.measures.offset, value: offsetText(measures.offset), help: copy.measures.offsetHelp },
    {
      key: "compression",
      label: copy.measures.compression,
      value: compressionText(measures.compression),
      help: copy.measures.compressionHelp,
    },
  ];
  return (
    <section aria-labelledby="measures-title" className="mt-8 max-w-2xl">
      <h2 id="measures-title" className="text-headline text-ink">
        {copy.measures.title}
      </h2>
      <p className={`${LINE} mt-1 text-ink-secondary`}>
        {measures.pairs > 0 ? copy.measures.pairs(formatNumber(measures.pairs)) : copy.measures.noPairs}
      </p>
      <dl className="mt-3 flex flex-col border-t border-hairline">
        {items.map((item) => (
          <div
            key={item.key}
            data-measure={item.key}
            className="grid grid-cols-[1fr_auto] items-baseline gap-x-4 border-b border-hairline py-3"
          >
            <dt className={`${LINE} font-semibold text-ink`}>{item.label}</dt>
            <dd className={`${LINE} text-right text-ink tabular-nums`}>{item.value}</dd>
            <dd className={`${LINE} col-span-2 mt-1 text-ink-secondary`}>{item.help}</dd>
          </div>
        ))}
      </dl>
      <h3 id="by-length-title" className="mt-6 text-label text-ink">
        {copy.byLength.title}
      </h3>
      <div
        role="region"
        aria-labelledby="by-length-title"
        tabIndex={0}
        className="mt-2 max-w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <table data-by-length="" className={`w-full border-collapse text-left text-ink ${LINE}`}>
          <thead>
            <tr className="border-b border-axis">
              <th scope="col" className="py-2 pr-4 text-label text-ink">
                {copy.byLength.band}
              </th>
              <th scope="col" className="px-3 py-2 text-right text-label text-ink">
                {copy.byLength.pairs}
              </th>
              <th scope="col" className="px-3 py-2 text-right text-label text-ink">
                {copy.measures.exact}
              </th>
              <th scope="col" className="py-2 pl-3 text-right text-label text-ink">
                {copy.measures.withinOne}
              </th>
            </tr>
          </thead>
          <tbody>
            {measures.by_length.map((band) => (
              <tr key={band.band} data-band={band.band} className="border-b border-hairline">
                <th scope="row" className="py-2 pr-4 text-left font-normal">
                  {copy.byLength.bands[band.band] ?? band.band}
                </th>
                <td className="px-3 py-2 text-right tabular-nums">{formatNumber(band.pairs)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{percentText(band.exact)}</td>
                <td className="py-2 pl-3 text-right tabular-nums">{percentText(band.within_one)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SideBySide({ page }: { page: ControlResults }) {
  if (page.rows.length === 0) {
    return <p className={`${LINE} mt-8 text-ink`}>{copy.empty}</p>;
  }
  const headings = page.scorers.map((scorer, index) => scorerHeading(scorer.name, index));
  return (
    <section aria-labelledby="side-by-side-title" className="mt-10">
      <h2 id="side-by-side-title" className="text-headline text-ink">
        {copy.table.title}
      </h2>
      <div
        role="region"
        aria-labelledby="side-by-side-title"
        tabIndex={0}
        className="mt-3 max-w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <table data-side-by-side="" className={`w-full border-collapse text-left text-ink ${LINE}`}>
          <thead>
            <tr className="border-b border-axis">
              <th scope="col" className="sticky left-0 z-10 bg-paper py-2 pr-4 text-label text-ink">
                {copy.table.answer}
              </th>
              <th scope="col" className="px-3 py-2 text-label text-ink">
                {copy.table.type}
              </th>
              <th scope="col" className="px-3 py-2 text-right text-label text-ink">
                {copy.table.words}
              </th>
              {headings.map((heading, index) => (
                <th key={index} scope="col" className="px-3 py-2 text-right text-label text-ink">
                  {heading}
                </th>
              ))}
              <th scope="col" className="py-2 pl-3 text-right text-label text-ink">
                {copy.table.ai}
              </th>
            </tr>
          </thead>
          <tbody>
            {page.rows.map((row) => (
              <tr key={row.number} data-row={row.number} className="border-b border-hairline">
                <th scope="row" className="sticky left-0 bg-paper py-2 pr-4 text-left font-normal whitespace-nowrap">
                  {answerLabel(row.number)}
                </th>
                <td className="px-3 py-2 whitespace-nowrap">{typeText(row.type)}</td>
                <td className="px-3 py-2 text-right tabular-nums">{formatNumber(row.words)}</td>
                {row.human.map((step, index) => (
                  <td key={index} className="px-3 py-2 text-right tabular-nums whitespace-nowrap">
                    {humanCell(step)}
                  </td>
                ))}
                <td data-ai="" className="py-2 pl-3 text-right tabular-nums whitespace-nowrap">
                  {aiCell(row.ai, page.withheld)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4">
        <Link href={ADMIN_CONTROL_TESTS_PATH} standalone>
          {tests.title}
        </Link>
      </p>
    </section>
  );
}
