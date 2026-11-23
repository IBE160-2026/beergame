"use client";

import { useState } from "react";

import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { usePageState } from "@/lib/page-state";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { ADMIN_CROSS_INSTITUTION_PATH, HOME_PATH } from "@/modules/identity/homes";
import { NotFoundPage } from "@/modules/identity/not-found-page";
import { PageShell } from "@/modules/identity/page-shell";

import { comparableText, measureName } from "./cross-class";
import type { ChosenFilters } from "./cross-class-api";
import { CompareBars, Filters } from "./cross-class-page";
import { institutionRows } from "./cross-institution";
import {
  type ComparedInstitution,
  type CrossInstitution,
  crossInstitutionKey,
  type InstitutionMeasure,
  useInstitutionStatistics,
} from "./cross-institution-api";
import { SECONDARY, Section, Table, TEXT, Toggled } from "./class-report-parts";

const copy = nb.crossInstitution;
const words = nb.crossClass;

/**
 * «Tverrinstitusjonell statistikk» (Story 14.7, cut list, FR-65, FR-5, AD-12, AD-14) in the
 * Admin-område: the stored aggregates grouped by Institution, «Samme mål, samme regnestykke.», as
 * Tverrklasse-statistikk draws its Class sessions: one row of `aria-hidden` bars per measure with
 * «Vis som tabell», Story 14.4's filters and «Ulikt oppsett» labels. No Class, Lecturer or Student
 * is named. A withheld Institution and a withheld or unmeasured figure are said in words. Every
 * number is the api's (AD-10). While `FEATURE_CROSS_INSTITUTION_STATS` is off the page does not
 * exist (the not-found page); anyone but the Admin sees the permission-denied page.
 */
export function CrossInstitutionPage() {
  return (
    <GuardedPage page="adminArea">
      {(user, updatedAt) =>
        user.cross_institution_stats ? <View user={user} updatedAt={updatedAt} /> : <NotFoundPage />
      }
    </GuardedPage>
  );
}

function View({ user, updatedAt }: { user: SessionUser; updatedAt: number }) {
  const [chosen, setChosen] = useState<ChosenFilters>({});
  const [changed, setChanged] = useState(false);
  const found = useInstitutionStatistics(chosen);
  const { phase, retry } = usePageState(found, crossInstitutionKey);
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  // The flag turned off since `/me` was read: the view no longer exists (AD-17).
  if (found.error instanceof ApiRequestError && found.error.status === 404) return <NotFoundPage />;
  const data = found.data;
  const crumbs = [
    { label: nb.homes.adminArea, href: HOME_PATH.adminArea },
    { label: copy.title, href: ADMIN_CROSS_INSTITUTION_PATH },
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
  data: CrossInstitution;
  chosen: ChosenFilters;
  announce: boolean;
  onChoose: (chosen: ChosenFilters) => void;
}) {
  if (data.ready === 0) {
    return (
      <p className={`mt-2 ${TEXT}`} data-cross-institution-empty="">
        {copy.empty}
      </p>
    );
  }
  return (
    <div className="mt-2 flex min-w-0 flex-col" data-cross-institution="">
      <p className={`${TEXT} font-semibold`}>{copy.intro}</p>
      <p className={`mt-1 ${SECONDARY}`}>{copy.about}</p>
      {data.institutions
        .filter((institution) => institution.withheld)
        .map((institution) => (
          <p key={institution.institution_id} className={`mt-1 ${SECONDARY}`} data-cross-institution-withheld="">
            {copy.withheldNote(institution.name)}
          </p>
        ))}
      {data.filters.length > 0 ? <Filters filters={data.filters} chosen={chosen} onChoose={onChoose} /> : null}
      <p aria-live="polite" className="sr-only" data-cross-institution-announce="">
        {announce ? copy.comparing(data.compared, data.ready) : ""}
      </p>
      {data.institutions.length === 0 ? (
        <p className={`mt-6 ${TEXT}`} data-cross-institution-too-few="">
          {copy.tooFewMatch}
        </p>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-x-16 gap-y-10 lg:grid-cols-2">
          {data.measures.map((measure) => (
            <Measure key={measure.key} measure={measure} institutions={data.institutions} />
          ))}
        </div>
      )}
    </div>
  );
}

function Measure({
  measure,
  institutions,
}: {
  measure: InstitutionMeasure;
  institutions: readonly ComparedInstitution[];
}) {
  const name = measureName(measure.key);
  const rows = institutionRows(measure, institutions);
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
            columns={[copy.institutionColumn, words.valueColumn, copy.sessionsColumn, words.differsColumn]}
            rows={rows.map((row) => ({
              key: row.key,
              head: row.session,
              cells: [row.figure, String(row.sessions), row.differs ?? words.sameSetup],
            }))}
          />
        }
      />
    </Section>
  );
}

