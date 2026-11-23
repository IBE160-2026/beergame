"use client";

// A client module because the Debrief's own AI-text marking (`modules/debrief/ai-text.tsx`) reads a
// client module: the print route still renders it on the server to complete HTML, and WeasyPrint
// runs no script (AD-18).
import { nb } from "@/copy/nb";
import { DebriefText } from "@/modules/debrief/ai-text";

import { reportCopy, reportDateTime } from "./copy";
import { type DebriefSection, debriefLine } from "./parts";

const copy = reportCopy.debrief;
const moment = nb.replay.walkthrough;
const TEXT = "text-body text-ink";
const KEEP = "break-after-avoid";

/**
 * The Debrief section (Story 13.10, FR-58, FR-47): the Explanation as written, whether and when the
 * Debrief was finished, its key moments with the line that ties them together, the answers on
 * evidence and structure (never those on feelings, said in a line), and the quiz attempts. AI text
 * (the line, a moment's sentence) reads «KI-generert, kan ta feil: «…»» and carries
 * `data-ai-generated`, which the render turns into the PDF's machine-readable mark (FR-34, UX-DR69).
 * Nothing of another Student.
 */
export function DebriefSectionView({ section }: { section: DebriefSection }) {
  return (
    <section aria-labelledby="report-debrief" className="mt-8" data-section="debrief">
      <h2 id="report-debrief" className="text-step-title font-semibold text-ink">
        {copy.title}
      </h2>

      <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{copy.explanation}</h3>
      {section.explanation !== null ? (
        <>
          <p className={`mt-1 ${TEXT} border-l-2 border-axis pl-3 whitespace-pre-wrap`} data-explanation="">
            {section.explanation}
          </p>
          {section.explanation_saved_at ? (
            <p className="mt-1 text-label text-ink-secondary">{copy.sent(reportDateTime(section.explanation_saved_at))}</p>
          ) : null}
        </>
      ) : (
        <p className={`mt-1 ${TEXT}`}>{copy.noExplanation}</p>
      )}

      <p className={`mt-4 ${TEXT}`} data-debrief-finished="">
        {debriefLine(section)}
      </p>

      {section.finished_at ? (
        <>
          <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{copy.moments}</h3>
          {section.moments.length === 0 ? (
            <p className={`mt-1 ${TEXT}`}>{copy.noMoments}</p>
          ) : (
            <ol className="mt-1 flex list-none flex-col gap-3 pl-0" data-moments="">
              {section.moments.map((each, i) => (
                <li key={i} className="break-inside-avoid">
                  <p className={`${TEXT} font-semibold`}>
                    <DebriefText text={each.heading} />
                  </p>
                  <p className={`mt-1 ${TEXT}`}>
                    {`${moment.reckoned}: `}
                    <DebriefText text={each.reckoning} />
                  </p>
                  <p className={`mt-1 ${TEXT}`}>
                    {`${moment.later}: `}
                    <DebriefText text={each.later} />
                  </p>
                  {each.patterns.map((pattern, i) => (
                    <p key={i} className={`mt-1 ${TEXT}`}>
                      {`${moment.pattern}: `}
                      <DebriefText text={pattern} />
                    </p>
                  ))}
                </li>
              ))}
            </ol>
          )}
          {section.narration ? (
            <>
              <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{copy.narration}</h3>
              <p className={`mt-1 ${TEXT}`} data-narration="">
                <DebriefText text={section.narration} />
              </p>
            </>
          ) : null}

          <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{copy.reflection}</h3>
          {section.reflection.length === 0 ? (
            <p className={`mt-1 ${TEXT}`}>{copy.noReflection}</p>
          ) : (
            <ol className="mt-1 flex list-none flex-col gap-3 pl-0" data-reflection="">
              {section.reflection.map((answer, i) => (
                <li key={i} className="break-inside-avoid">
                  <p className={TEXT}>{answer.prompt}</p>
                  <p className={`mt-1 ${TEXT} border-l-2 border-axis pl-3 whitespace-pre-wrap`}>{answer.text}</p>
                </li>
              ))}
            </ol>
          )}
          <p className="mt-2 text-label text-ink-secondary" data-reflection-note="">
            {copy.reflectionNote}
          </p>
        </>
      ) : null}

      <h3 className={`mt-4 text-label font-semibold text-ink ${KEEP}`}>{copy.quiz}</h3>
      <p className={`mt-1 ${TEXT}`} data-quiz="">
        {copy.attempts(section.quiz_attempts, section.quiz_passed)}
      </p>
    </section>
  );
}
