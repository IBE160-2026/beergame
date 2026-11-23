"use client";

import { useId, useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import { cn } from "@/lib/utils";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { crossClassPath, HOME_PATH } from "@/modules/identity/homes";
import { PageShell } from "@/modules/identity/page-shell";

import {
  comparableText,
  type CompareRow,
  compareRows,
  measureName,
  nothingToCompare,
  optionName,
  sessionName,
  splitSessions,
} from "./cross-class";
import {
  type ChosenFilters,
  type CompareFilter,
  type ComparedMeasure,
  type ComparedSession,
  type CrossClass,
  crossClassKey,
  useClassStatistics,
} from "./cross-class-api";
import { SECONDARY, Section, Table, TEXT, Toggled } from "./class-report-parts";

const copy = nb.crossClass;

/**
 * Tverrklasse-statistikk (Story 14.3, FR-65, UX-DR55, `09-alle-sider.png`): the Lecturer's own
 * Class sessions compared on the stored aggregates, «Samme mål, samme regnestykke.». Each measure
 * is a row of `aria-hidden` bars, one per Class session with an aggregate, the value printed and
 * read beside it, with «Vis som tabell» under it. A figure withheld because its group held fewer
 * than 10 Students, or not measured, is said in words and has no bar. Every number is the api's
 * (AD-10); anyone without the Lecturer role sees the permission-denied page.
 *
 * Story 14.4 (FR-65, NFR-6): the filters above the charts, one group per dimension of text
 * buttons with `aria-pressed` and counts, refetch the comparison and say politely how many Class
 * sessions it now compares. A compared Class session that differs from the others is labelled in
 * words in its bar row, the bar's SVG `<title>` and the table; a score measure says whether the
 * scores can be compared.
 */
export function CrossClassPage() {
  return <GuardedPage page="lecturerHome">{(user, updatedAt) => <View user={user} updatedAt={updatedAt} />}</GuardedPage>;
}

function View({ user, updatedAt }: { user: SessionUser; updatedAt: number }) {
  const [chosen, setChosen] = useState<ChosenFilters>({});
  const [changed, setChanged] = useState(false);
  const found = useClassStatistics(chosen);
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
      {data ? (
        <Comparison
          data={data}
          chosen={chosen}
          announce={changed && !found.isPlaceholderData}
          onChoose={(next) => {
            setChosen(next);
            setChanged(true);
          }}
        />
      ) : null}
    </PageShell>
  );
}

function Comparison({
  data,
  chosen,
  announce,
  onChoose,
}: {
  data: CrossClass;
  chosen: ChosenFilters;
  announce: boolean;
  onChoose: (chosen: ChosenFilters) => void;
}) {
  if (nothingToCompare(data)) {
    return (
      <p className={`mt-2 ${TEXT}`} data-cross-class-empty="">
        {copy.empty}
      </p>
    );
  }
  const { ready, compared, waiting } = splitSessions(data);
  return (
    <div className="mt-2 flex min-w-0 flex-col" data-cross-class="">
      <p className={`${TEXT} font-semibold`}>{copy.intro}</p>
      <p className={`mt-1 ${SECONDARY}`}>{copy.about}</p>
      {ready.length < 2 ? (
        <p className={`mt-4 ${TEXT}`} data-cross-class-none-ready="">
          {copy.noneReady}
        </p>
      ) : (
        <>
          <Filters filters={data.filters} chosen={chosen} onChoose={onChoose} />
          <p aria-live="polite" className="sr-only" data-cross-class-announce="">
            {announce ? copy.comparing(compared.length, ready.length) : ""}
          </p>
          {compared.length < 2 ? (
            <p className={`mt-6 ${TEXT}`} data-cross-class-too-few="">
              {copy.tooFewMatch}
            </p>
          ) : (
            <div className="mt-8 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
              {data.measures.map((measure) => (
                <Measure key={measure.key} measure={measure} sessions={compared} />
              ))}
            </div>
          )}
        </>
      )}
      {waiting.length > 0 ? <Waiting sessions={waiting} /> : null}
    </div>
  );
}

function Measure({ measure, sessions }: { measure: ComparedMeasure; sessions: readonly ComparedSession[] }) {
  const name = measureName(measure.key);
  const rows = compareRows(measure, sessions);
  const slug = measure.key.replaceAll(".", "-");
  const comparable = comparableText(measure);
  return (
    <Section title={name} name={slug} intro={comparable ?? undefined}>
      <Toggled
        name={slug}
        chart={<CompareBars rows={rows} name={slug} />}
        table={
          <Table
            name={slug}
            caption={comparable ? `${copy.tableCaption(name)}. ${comparable}` : copy.tableCaption(name)}
            columns={[copy.sessionColumn, copy.valueColumn, copy.differsColumn]}
            rows={rows.map((row) => ({
              key: row.key,
              head: row.session,
              cells: [row.text, row.differs ?? copy.sameSetup],
            }))}
          />
        }
      />
    </Section>
  );
}

/** One bar per Class session, its value printed beside it; the words are read, the bars are not. */
export function CompareBars({ rows, name }: { rows: readonly CompareRow[]; name: string }) {
  return (
    <ol className="mt-1" data-compare-bars={name}>
      {rows.map((row) => (
        <li
          key={row.key}
          className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 py-1 text-body-phone lg:grid-cols-[minmax(0,min(12rem,40%))_minmax(4rem,1fr)_auto] lg:text-body"
          data-compare-row=""
        >
          <span className="sr-only">{row.reads}</span>
          <span aria-hidden="true" className="[overflow-wrap:anywhere]">
            {row.session}
            {row.differs ? (
              <span className="block text-caption text-ink-secondary" data-compare-differs="">
                {row.differs}
              </span>
            ) : null}
          </span>
          <span aria-hidden="true" className="order-last col-span-2 flex h-3 min-w-0 lg:order-none lg:col-span-1">
            {/* The bar's `<title>` holds the row's reading, its difference label included (NFR-6). */}
            <svg className="block h-3 w-full overflow-visible" data-compare-bar="">
              <title>{row.reads}</title>
              {row.share != null ? (
                <rect className="fill-order-history" x="0" y="0" height="100%" width={`${(row.share * 100).toFixed(2)}%`} />
              ) : null}
            </svg>
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

/** The filters (Story 14.4): one group per dimension, «Alle» and each stored value, one pressed per
 * group, the api's counts beside them; as the Matrisevegg's `WallFilters`. */
export function Filters({
  filters,
  chosen,
  onChoose,
}: {
  filters: readonly CompareFilter[];
  chosen: ChosenFilters;
  onChoose: (chosen: ChosenFilters) => void;
}) {
  return (
    <section
      aria-label={copy.filtersLabel}
      className="mt-6 flex flex-wrap items-center gap-x-8 gap-y-1 text-caption"
      data-cross-class-filters=""
    >
      {filters.map((filter) => {
        // The Lecturer's own choice, at once while its answer loads; a value the list no longer
        // holds reads as «Alle», as the api ignores it.
        const value = chosen[filter.dimension];
        const pressed = filter.options.some((option) => option.value === value) ? value! : null;
        return (
          <FilterGroup
            key={filter.dimension}
            filter={filter}
            pressed={pressed}
            onChoose={(value) => {
              const next = { ...chosen };
              if (value == null) delete next[filter.dimension];
              else next[filter.dimension] = value;
              onChoose(next);
            }}
          />
        );
      })}
    </section>
  );
}

function FilterGroup({
  filter,
  pressed,
  onChoose,
}: {
  filter: CompareFilter;
  pressed: string | null;
  onChoose: (value: string | null) => void;
}) {
  const id = useId();
  const choices: { value: string | null; label: string; count: number }[] = [
    { value: null, label: copy.all, count: filter.all_count },
    ...filter.options.map((option) => ({
      value: option.value,
      label: optionName(filter.dimension, option),
      count: option.count,
    })),
  ];
  return (
    <div role="group" aria-labelledby={id} className="flex flex-wrap items-center gap-x-3" data-filter-group={filter.dimension}>
      <span id={id} className="text-ink-secondary">
        {copy.dimensions[filter.dimension]}
      </span>
      {choices.map((choice) => {
        const on = choice.value === pressed;
        return (
          <button
            key={choice.value ?? "all"}
            type="button"
            aria-pressed={on}
            onClick={() => onChoose(choice.value)}
            className={cn(
              "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center justify-center gap-1 text-ink tabular-nums lining-nums [overflow-wrap:anywhere] hover:underline",
              "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
              on && "font-semibold underline underline-offset-4",
            )}
            data-filter={choice.value ?? "all"}
          >
            {choice.label}
            <span className="font-normal text-ink-secondary">{choice.count}</span>
          </button>
        );
      })}
    </div>
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
