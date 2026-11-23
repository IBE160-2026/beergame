import type { ReactNode } from "react";

import type { components } from "@/lib/api/schema";
import { formatNumber } from "@/lib/number-format";

import { AssessmentSectionView } from "./assessment-section";
import { reportCopy } from "./copy";
import { DebriefSectionView } from "./debrief-section";
import { GameSectionView } from "./game-section";
import { ReplaySectionView } from "./replay-section";
import { TestSectionView } from "./test-section";

export type ReportData = components["schemas"]["ReportDataOut"];
export type ReportSectionData = ReportData["sections"][number];
export type CompletionSection = components["schemas"]["CompletionSectionOut"];

const copy = reportCopy.completion;
const TEXT = "text-body text-ink";

/** «70 %», through the shared Norwegian number formatter. */
function percent(value: number): string {
  return `${formatNumber(value)} %`;
}

/** The step's status in words, never by mark alone (UX-DR54): «gjort», «ikke gjort», and «…,
 * rettet av faglærer» when a correction decided it. */
export function stepStatus(step: CompletionSection["steps"][number]): string {
  const status = step.done ? copy.done : copy.notDone;
  return step.corrected ? copy.corrected(status) : status;
}

/** The share lines under the table, as the Studentside writes them; none without a share. */
export function shareLines(section: CompletionSection): string[] {
  if (!section.obligatory || section.ordered_share == null) return [];
  const ordered = percent(section.ordered_share);
  const lines = [
    `${section.share_game ? copy.orderedIn(ordered, section.share_game) : copy.ordered(ordered)} ${copy.required(percent(section.required_share))}`,
  ];
  if (section.playout_share) lines.push(copy.playout(percent(section.playout_share)));
  return lines;
}

/** «Kravet er oppfylt.», «Kravet er ikke oppfylt.», or that the Klasseøkt is not obligatory. */
export function requirementLine(section: CompletionSection): string {
  if (!section.obligatory || section.requirement_met == null) return copy.notObligatory;
  return section.requirement_met ? copy.met : copy.notMet;
}

/** «Fullføring» (FR-17, FR-58): the status per step as a table with header cells and scopes,
 * then the share line and whether the requirement is met. */
function CompletionSectionView({ section }: { section: CompletionSection }) {
  return (
    <section aria-labelledby="report-completion" className="mt-8">
      <h2 id="report-completion" className="text-step-title font-semibold text-ink">
        {copy.title}
      </h2>
      <table className="mt-3 w-full table-fixed border-collapse text-body">
        <caption className="text-left text-label text-ink-secondary">{copy.caption}</caption>
        <thead>
          <tr className="border-b border-axis">
            <th scope="col" className="w-2/5 py-1 pr-4 text-left font-semibold">
              {copy.step}
            </th>
            <th scope="col" className="py-1 text-left font-semibold">
              {copy.status}
            </th>
          </tr>
        </thead>
        <tbody>
          {section.steps.map((step) => (
            <tr key={step.step} className="border-b border-hairline" data-step={step.step}>
              <th scope="row" className="py-1 pr-4 text-left font-normal">
                {copy.steps[step.step]}
              </th>
              <td className="py-1">{stepStatus(step)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {shareLines(section).map((line) => (
        <p key={line} className={`mt-3 ${TEXT}`}>
          {line}
        </p>
      ))}
      <p className={`mt-3 font-semibold ${TEXT}`} data-requirement="">
        {requirementLine(section)}
      </p>
    </section>
  );
}

type Renderers = {
  [K in ReportSectionData["kind"]]: (props: { section: Extract<ReportSectionData, { kind: K }> }) => ReactNode;
};

/** The print route's section registry, in step with `SECTIONS` in `backend/app/modules/reports/
 * report_data.py`: each `kind` the api builds has its renderer here. `completion` (Story 13.7),
 * `game` (Story 13.8, `game-section.tsx`), `debrief`, `replay` and `test` (Story 13.10), and
 * `assessment` (Story 13.11, only when the Student added it, `assessment-section.tsx`). Each
 * renders its charts from `components/charts` at a fixed width with a table after every chart. */
export const SECTIONS: Renderers = {
  completion: CompletionSectionView,
  game: GameSectionView,
  debrief: DebriefSectionView,
  replay: ReplaySectionView,
  test: TestSectionView,
  assessment: AssessmentSectionView,
};

export function ReportSection({ section }: { section: ReportSectionData }) {
  const Render = SECTIONS[section.kind] as (props: { section: ReportSectionData }) => ReactNode;
  return <Render section={section} />;
}
