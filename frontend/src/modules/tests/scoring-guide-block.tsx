"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { TextAreaField } from "@/components/text-area-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";

import {
  GUIDE_TEXT_MAX,
  type GuideQuestion,
  guideBody,
  guideTextProblem,
  type ScoringGuide,
  type ScoringGuideBody,
  saveScoringGuide,
  scoringGuideKey,
  useScoringGuide,
} from "./api";

const copy = nb.tests.scoringGuide;
const LINE = "text-body-phone lg:text-body";

/**
 * The Klasseøkt's «Sensorveiledning» block (Story 11.2, FR-81, UX-DR49, AD-12, AD-27): the one
 * five-step scale, then per long-answer question and Adapted item template its title, «Standard»
 * or «Endret», one Tekstfelt with the descriptive guide text (label above it) and the coded
 * criteria as a read-only table under it. «Ikke kontrollert med en Kontrolltest.» shows for every
 * version no Control test has checked. Its own secondary save sends only the texts the Lecturer
 * changed; from the original Test deadline, for an Assistant lecturer and for an archived Class the
 * block is read-only text. Nothing renders for a User the api refuses.
 */
export function ScoringGuideBlock({ classSessionId }: { classSessionId: string }) {
  const found = useScoringGuide(classSessionId);
  const titleId = useId();
  if (found.data) return <ScoringGuideView guide={found.data} classSessionId={classSessionId} titleId={titleId} />;
  if (!found.isError) return null;
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") return null;
  return (
    <section aria-labelledby={titleId} className="mt-12 border-t border-hairline pt-8">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <div className="mt-3 flex flex-col items-start gap-2">
        <ActionError message={copy.loadFailed} />
        <Button onClick={() => void found.refetch()}>{nb.system.retry}</Button>
      </div>
    </section>
  );
}

function ScoringGuideView({ guide, classSessionId, titleId }: { guide: ScoringGuide; classSessionId: string; titleId: string }) {
  const queryClient = useQueryClient();
  const ids = useId();
  // The texts the Lecturer touched, until «Lagre sensorveiledning»; the rest follow the api.
  const [draft, setDraft] = useState<{ versionId: string; texts: Readonly<Record<string, string>> } | null>(null);
  const [saved, setSaved] = useState(false);
  const editable = guide.can_change && guide.open;
  // A refetch that brings another version (another owner's save) drops the draft made on the old one.
  const texts = draft && draft.versionId === guide.version_id ? draft.texts : {};
  const body = guideBody(guide, texts);
  const save = useAction({
    mutationFn: async (sent: ScoringGuideBody) => {
      try {
        return await saveScoringGuide(classSessionId, sent);
      } catch (error) {
        // Closed meanwhile (the Test deadline passed, the Class archived): read the block again, so
        // it shows its read-only state instead of fields that can no longer save.
        if (error instanceof ApiRequestError && ["scoring_guide_locked", "class_archived"].includes(error.code)) {
          setDraft(null);
          void queryClient.invalidateQueries({ queryKey: scoringGuideKey(classSessionId) });
        }
        throw error;
      }
    },
    messages: {
      scoring_guide_locked: copy.closed,
      class_archived: copy.archived,
      validation_error: copy.invalid,
    },
    fallback: copy.failed,
    onSuccess: (result) => {
      queryClient.setQueryData(scoringGuideKey(classSessionId), result);
      setDraft(null);
      setSaved(true);
    },
  });
  const change = (id: string, text: string) => {
    setSaved(false);
    save.reset();
    setDraft({ versionId: guide.version_id, texts: { ...texts, [id]: text } });
  };
  const readOnly = !guide.can_change ? copy.assistant : !guide.open ? copy.closed : null;
  return (
    <section aria-labelledby={titleId} className="mt-12 border-t border-hairline pt-8" data-scoring-guide="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.help}</p>
      {guide.draft ? (
        <p data-scoring-guide-draft="" className={`${LINE} mt-2 max-w-2xl font-semibold text-ink`}>
          {copy.draft}
        </p>
      ) : null}
      {guide.checked ? null : (
        <p data-scoring-guide-unchecked="" className={`${LINE} mt-2 max-w-2xl text-ink`}>
          {copy.unchecked}
        </p>
      )}
      {guide.outdated ? <p className={`${LINE} mt-2 max-w-2xl text-ink`}>{copy.outdated}</p> : null}
      {readOnly ? <p className={`${LINE} mt-2 max-w-2xl text-ink`}>{readOnly}</p> : null}

      <h3 id={`${ids}-scale`} className={`${LINE} mt-6 font-semibold text-ink`}>
        {copy.scaleHeading}
      </h3>
      <ol aria-labelledby={`${ids}-scale`} className="mt-2 flex max-w-3xl flex-col gap-1" data-scoring-scale="">
        {guide.scale.map((step) => (
          <li key={step.step} className={`${LINE} flex gap-3 text-ink`}>
            <span className="w-4 shrink-0 font-semibold tabular-nums">{step.step}</span>
            <span className="min-w-0">{step.label}</span>
          </li>
        ))}
      </ol>

      <ol className="mt-6 flex max-w-3xl flex-col">
        {guide.questions.map((question, i) => (
          <GuideRow
            key={question.id}
            question={question}
            idBase={`${ids}-g${i}`}
            editable={editable}
            value={texts[question.id] ?? question.guide}
            touched={texts[question.id] !== undefined}
            onChange={(text) => change(question.id, text)}
          />
        ))}
      </ol>

      {editable ? (
        <div className="mt-4 flex flex-col items-start gap-3">
          <Button
            variant="secondary"
            unavailable={save.isPending || body === null}
            onClick={() => {
              if (save.isPending || body === null) return;
              setSaved(false);
              save.mutate(body);
            }}
          >
            {save.isPending ? copy.saving : copy.save}
          </Button>
          <ActionError message={save.errorMessage} />
          <p role="status" className="text-body-phone text-ink">
            {saved && !save.isError ? copy.saved : ""}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function GuideRow({
  question,
  idBase,
  editable,
  value,
  touched,
  onChange,
}: {
  question: GuideQuestion;
  idBase: string;
  editable: boolean;
  value: string;
  touched: boolean;
  onChange: (text: string) => void;
}) {
  const titleId = `${idBase}-title`;
  // «Endret» while the text differs from the default it derives from, also before it is saved.
  const changed = touched ? value !== question.standard_guide : question.changed;
  const problem = touched ? guideTextProblem(value) : null;
  const error = problem === "empty" ? copy.emptyGuide : problem === "tooLong" ? copy.tooLong(GUIDE_TEXT_MAX) : undefined;
  return (
    <li data-guide={question.id} data-changed={changed ? "" : undefined} className="border-t border-axis py-6">
      <h3 id={titleId} className={`${LINE} font-semibold text-ink`}>
        {question.title}
      </h3>
      <p className="mt-1 text-body-phone text-ink-secondary">
        {copy.kinds[question.kind] ?? question.kind} ·{" "}
        <span data-guide-mark="" className="font-semibold text-ink">
          {changed ? copy.changed : copy.standard}
        </span>
      </p>
      {editable ? (
        <TextAreaField
          id={`${idBase}-text`}
          label={copy.guideLabel}
          aria-labelledby={`${titleId} ${idBase}-text-label`}
          hint={copy.guideHint}
          rows={5}
          className="mt-4"
          value={value}
          error={error}
          onChange={(event) => onChange(event.target.value)}
        />
      ) : (
        <div className="mt-4">
          <p className="text-label text-ink">{copy.guideLabel}</p>
          <p className={`${LINE} mt-1 whitespace-pre-line text-ink`}>{question.guide}</p>
        </div>
      )}
      <table className="mt-4 w-full border-collapse text-left" data-guide-criteria="">
        <caption className="mb-2 text-left text-label text-ink">{copy.criteriaCaption}</caption>
        <thead>
          <tr className="border-b border-axis">
            <th scope="col" className="w-16 py-2 pr-3 text-body-phone font-semibold text-ink-secondary">
              {copy.code}
            </th>
            <th scope="col" className="py-2 pr-3 text-body-phone font-semibold text-ink-secondary">
              {copy.criterion}
            </th>
            <th scope="col" className="w-16 py-2 text-right text-body-phone font-semibold text-ink-secondary">
              {copy.weight}
            </th>
          </tr>
        </thead>
        <tbody>
          {question.criteria.map((criterion) => (
            <tr key={criterion.code} className="border-b border-hairline align-top">
              <th scope="row" className="py-2 pr-3 text-body-phone font-semibold text-ink">
                {criterion.code}
              </th>
              <td className="py-2 pr-3 text-body-phone text-ink">{criterion.text}</td>
              <td className="py-2 text-right text-body-phone tabular-nums text-ink">{copy.weightText(criterion.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </li>
  );
}
