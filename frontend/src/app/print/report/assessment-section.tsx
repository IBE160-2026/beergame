import type { components } from "@/lib/api/schema";
import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";

import { reportCopy } from "./copy";

export type AssessmentSection = components["schemas"]["AssessmentSectionOut"];
export type AssessedReportItem = AssessmentSection["items"][number];

const copy = reportCopy.assessment;
const student = nb.assessment.student;
const TEXT = "text-body text-ink";
const KEEP = "break-after-avoid";

type ReportText = AssessedReportItem["title"];

/** Text as shown (FR-34, UX-DR69), as `DebriefText` writes it but without a client module (this
 * section renders on the server): AI text as «KI-generert, kan ta feil: «…»» on a `span` marked
 * `data-ai-generated="true"`; only `ai_generated` decides. */
function ShownText({ text }: { text: ReportText }) {
  if (!text.ai_generated) return <>{text.text}</>;
  return <span data-ai-generated="true">{nb.debrief.aiText(text.text)}</span>;
}

/** «7,5 av 10 poeng», or «Ikke vurdert ennå» (the Student's own view's words). */
export function itemPoints(item: Pick<AssessedReportItem, "points" | "weight">): string {
  return item.points == null ? student.notAssessed : student.points(formatNumber(item.points), formatNumber(item.weight));
}

/** The item's score in words: the AI's step on the scale with its label, or the computed result. */
export function itemScore(item: Pick<AssessedReportItem, "ai" | "computed">): string {
  if (item.ai) {
    if (!item.ai.assessed || item.ai.step == null) return student.notAssessed;
    return student.aiStep(formatNumber(item.ai.step), formatNumber(item.ai.top), item.ai.label ?? "");
  }
  return item.computed ? student.computed[item.computed] : "";
}

/**
 * «KI-vurdering» in the Student report (Story 13.11, FR-55, FR-56, FR-58, FR-34): only when the
 * Student added it. The disclosure first, then each item with its question, its score in words and
 * its points, the written feedback with «KI-generert, kan ta feil:» (or the note that it was left
 * out), the weighted total and the Indicative letter where the api gave one. Every AI text is on a
 * `p` or `span` with `data-ai-generated="true"`, which the render marks in the PDF's structure tree.
 */
export function AssessmentSectionView({ section }: { section: AssessmentSection }) {
  return (
    <section aria-labelledby="report-assessment" className="mt-8" data-section="assessment">
      <h2 id="report-assessment" className={`text-step-title font-semibold text-ink ${KEEP}`}>
        {copy.title}
      </h2>
      <p className={`mt-2 font-semibold ${TEXT}`} data-disclosure="">
        {student.disclosure}
      </p>
      <p className={`mt-1 ${TEXT}`}>{copy.added}</p>
      {section.checked ? null : (
        <p className={`mt-1 ${TEXT}`} data-unchecked="">
          {student.unchecked}
        </p>
      )}
      <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{student.itemsTitle}</h3>
      <ol className="list-none">
        {section.items.map((item) => (
          <AssessedItem key={item.number} item={item} />
        ))}
      </ol>
      <div className="mt-4 border-t border-axis pt-3 break-inside-avoid">
        <p className={`font-semibold ${TEXT}`} data-ai-generated="true" data-total="">
          {student.total(formatNumber(section.total), formatNumber(section.total_max))}
        </p>
        <p className="mt-1 text-label text-ink-secondary">{student.totalNote}</p>
        {section.letter ? (
          <div className="mt-3" data-letter={section.letter}>
            <p className={`font-semibold ${TEXT}`} data-ai-generated="true">
              {nb.assessment.letter.value(section.letter)}
            </p>
            <p className="mt-1 text-label text-ink-secondary">{nb.assessment.letter.label}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function AssessedItem({ item }: { item: AssessedReportItem }) {
  const ai = item.ai;
  return (
    <li className="mt-4 border-t border-hairline pt-3" data-assessed-item={item.number}>
      <h4 className={`text-label font-semibold text-ink ${KEEP}`}>{nb.tests.individual.item(item.number)}</h4>
      <p className={`mt-1 ${TEXT} ${KEEP}`}>
        <ShownText text={item.title} />
      </p>
      <p className={`mt-2 ${TEXT}`} data-ai-generated={ai ? "true" : undefined} data-score="">
        {itemScore(item)}
      </p>
      {/* An AI item's points come from the AI's step: marked as AI text too. */}
      <p className="mt-1 text-label text-ink-secondary" data-ai-generated={ai ? "true" : undefined}>
        {itemPoints(item)}
      </p>
      {ai?.feedback ? (
        <p className={`mt-2 ${TEXT}`} data-feedback="">
          <ShownText text={ai.feedback} />
        </p>
      ) : null}
      {ai?.feedback_dropped ? (
        <p className={`mt-2 ${TEXT}`} data-feedback-dropped="">
          {student.feedbackDropped}
        </p>
      ) : null}
    </li>
  );
}
