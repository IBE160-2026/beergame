import { formatNumber } from "@/lib/number-format";

import { reportCopy, reportDateTime } from "./copy";
import { type ReportData, ReportSection } from "./sections";

const DATES = ["start_at", "play_deadline", "debrief_deadline", "test_deadline"] as const;

/** The report: the header (the skeleton, FR-58) and then each section in the api's order. */
export function Report({ data }: { data: ReportData }) {
  const facts = reportCopy.facts;
  return (
    <main className="bg-paper text-ink">
      {/* A4 with room for a binder's holes; the report flows over as many pages as it needs. */}
      <style>{"@page { size: A4; margin: 18mm 16mm 20mm; }"}</style>
      <header>
        <p className="text-label font-semibold text-ink-secondary">{reportCopy.product}</p>
        <h1 className="mt-1 text-headline font-semibold">{reportCopy.title}</h1>
        <p className="mt-2 text-body">{reportCopy.purpose}</p>
        <dl className="mt-4 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1 text-body">
          <dt className="text-ink-secondary">{facts.student}</dt>
          <dd>{data.student_name}</dd>
          <dt className="text-ink-secondary">{facts.klass}</dt>
          <dd>{data.class_name}</dd>
          <dt className="text-ink-secondary">{facts.session}</dt>
          <dd>{formatNumber(data.session_number)}</dd>
          <dt className="text-ink-secondary">{facts.generated}</dt>
          <dd>{reportDateTime(data.generated_at)}</dd>
        </dl>
      </header>
      <section aria-labelledby="report-dates" className="mt-8">
        <h2 id="report-dates" className="text-step-title font-semibold">
          {reportCopy.dates.title}
        </h2>
        <table className="mt-3 w-full table-fixed border-collapse text-body">
          <caption className="text-left text-label text-ink-secondary">{reportCopy.dates.caption}</caption>
          <thead>
            <tr className="border-b border-axis">
              <th scope="col" className="w-2/5 py-1 pr-4 text-left font-semibold">
                {reportCopy.dates.name}
              </th>
              <th scope="col" className="py-1 text-left font-semibold">
                {reportCopy.dates.when}
              </th>
            </tr>
          </thead>
          <tbody>
            {DATES.map((name) => (
              <tr key={name} className="border-b border-hairline">
                <th scope="row" className="py-1 pr-4 text-left font-normal">
                  {reportCopy.dates[name]}
                </th>
                <td className="py-1">{data.dates[name] ? reportDateTime(data.dates[name]) : reportCopy.dates.none}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {data.sections.map((section, index) => (
        <ReportSection key={`${section.kind}-${index}`} section={section} />
      ))}
    </main>
  );
}
