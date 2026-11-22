"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { adaptedPreviewPath } from "@/modules/identity/homes";

import {
  draftOf,
  judgeDraft,
  type QuestionItem,
  type QuestionSet,
  type QuestionSetBody,
  type QuestionSetDraft,
  questionSetKey,
  saveQuestionSet,
  useQuestionSet,
} from "./api";

const copy = nb.tests.questionSet;
const LINE = "text-body-phone lg:text-body";
/** A question's row: its title, and under it on a phone, beside it on a wide block, its Vekt and
 * «Ta ut» in one line, bottom-aligned, so every Vekt field stands in one column. */
const ROW = "grid grid-cols-1 gap-3 @[40rem]:grid-cols-[minmax(0,1fr)_auto] @[40rem]:items-end @[40rem]:gap-x-8";
const CONTROLS = "flex flex-wrap items-end gap-x-4 gap-y-2";
const FIELD = "w-32";
const TOGGLE = "w-36 shrink-0";

/**
 * The Klasseøkt's «Spørsmål og vekter» block (Story 11.1, FR-52, FR-53, UX-DR49, AD-12): every
 * question of the Individual test with its type, its «Vekt i %» and «Ta ut», and one line for the
 * Adapted items' total weight, with a Lenke to their preview with a sample Student (Story 11.9).
 * The sum shows live and is announced politely; while it is not
 * 100 % «Lagre vekter» is unavailable (the api refuses such a save too). Taking out a question
 * that measures quantities warns without blocking. Its own secondary save, like «Lagre quizvalg»:
 * the selection belongs to the test. From the Start date, for an Assistant lecturer and for an
 * archived Class the block is read-only text. Nothing renders for a User the api refuses.
 */
export function QuestionSetBlock({ classSessionId }: { classSessionId: string }) {
  const found = useQuestionSet(classSessionId);
  const titleId = useId();
  if (found.data) return <QuestionSetView set={found.data} classSessionId={classSessionId} titleId={titleId} />;
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

function QuestionSetView({ set, classSessionId, titleId }: { set: QuestionSet; classSessionId: string; titleId: string }) {
  const queryClient = useQueryClient();
  const ids = useId();
  // The selection as edited, until «Lagre vekter»; null follows the api.
  const [draft, setDraft] = useState<QuestionSetDraft | null>(null);
  const [left, setLeft] = useState<ReadonlySet<string>>(new Set());
  const [saved, setSaved] = useState(false);
  const editable = set.can_change && set.open;
  // A refetch that brings another version (a new question set) drops the draft made on the old one.
  const shown = draft && draft.version === set.version ? draft : draftOf(set);
  const judged = judgeDraft(set, shown);
  const save = useAction({
    mutationFn: async (body: QuestionSetBody) => {
      try {
        return await saveQuestionSet(classSessionId, body);
      } catch (error) {
        // Closed meanwhile (the Start date passed, the Class archived): read the block again, so
        // it shows its read-only state instead of fields that can no longer save.
        if (error instanceof ApiRequestError && ["session_locked", "class_archived"].includes(error.code)) {
          setDraft(null);
          void queryClient.invalidateQueries({ queryKey: questionSetKey(classSessionId) });
        }
        throw error;
      }
    },
    messages: {
      weights_not_100: copy.notHundred,
      session_locked: copy.closed,
      class_archived: copy.archived,
    },
    fallback: copy.failed,
    onSuccess: (result) => {
      queryClient.setQueryData(questionSetKey(classSessionId), result);
      setDraft(null);
      setLeft(new Set());
      setSaved(true);
    },
  });
  const change = (next: QuestionSetDraft) => {
    setSaved(false);
    save.reset();
    setDraft(next);
  };
  const leave = (key: string) => setLeft((before) => new Set(before).add(key));
  const toggle = (id: string) => {
    const excluded = new Set(shown.excluded);
    if (excluded.has(id)) excluded.delete(id);
    else excluded.add(id);
    change({ ...shown, excluded });
  };
  const readOnly = !set.can_change ? copy.assistant : !set.open ? copy.closed : null;
  const blocked = judged.body === null || judged.sum !== 100;
  return (
    <section aria-labelledby={titleId} className="@container mt-12 border-t border-hairline pt-8" data-question-set="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <p className={`${LINE} mt-2 max-w-2xl text-ink-secondary`}>{copy.help}</p>
      {set.draft ? (
        <p data-question-set-draft="" className={`${LINE} mt-2 max-w-2xl font-semibold text-ink`}>
          {copy.draft}
        </p>
      ) : null}
      {set.outdated ? <p className={`${LINE} mt-2 max-w-2xl text-ink`}>{copy.outdated}</p> : null}
      {readOnly ? <p className={`${LINE} mt-2 max-w-2xl text-ink`}>{readOnly}</p> : null}
      <ol className="mt-6 flex max-w-4xl flex-col">
        {set.items.map((item, i) => (
          <QuestionRow
            key={item.id}
            item={item}
            idBase={`${ids}-q${i}`}
            editable={editable}
            excluded={shown.excluded.has(item.id)}
            value={shown.weights[item.id] ?? ""}
            error={
              judged.invalid.has(item.id) && (left.has(item.id) || (shown.weights[item.id] ?? "") !== "")
                ? copy.invalidWeight
                : undefined
            }
            onChange={(value) => change({ ...shown, weights: { ...shown.weights, [item.id]: value } })}
            onLeave={() => leave(item.id)}
            onToggle={() => toggle(item.id)}
          />
        ))}
        <li data-question-adapted="" className="border-t border-axis py-4">
          <div className={ROW}>
            <div className="min-w-0">
              <p id={`${ids}-adapted`} className={`${LINE} font-semibold text-ink`}>
                {copy.adaptedTitle}
              </p>
              <p id={`${ids}-adapted-help`} className="mt-1 text-body-phone text-ink-secondary">
                {copy.adaptedHelp} {copy.replacements(set.adapted.replacements)}
              </p>
              <p>
                <Link href={adaptedPreviewPath(classSessionId)} standalone data-adapted-preview-link="">
                  {copy.adaptedPreview}
                </Link>
              </p>
            </div>
            <div className={CONTROLS}>
              {editable ? (
                <TextField
                  id={`${ids}-adapted-weight`}
                  label={copy.weight}
                  aria-labelledby={`${ids}-adapted ${ids}-adapted-weight-label`}
                  inputMode="numeric"
                  className={FIELD}
                  value={shown.adapted}
                  error={
                    judged.invalid.has("adapted") && (left.has("adapted") || shown.adapted !== "") ? copy.invalidWeight : undefined
                  }
                  onChange={(event) => change({ ...shown, adapted: event.target.value })}
                  onBlur={() => leave("adapted")}
                />
              ) : (
                <p className={`${LINE} ${FIELD} text-ink`}>{copy.weightText(set.adapted.weight)}</p>
              )}
              {/* Keeps the Vekt fields in one column with the rows that have «Ta ut». */}
              {editable ? <span aria-hidden="true" className={`${TOGGLE} hidden @[40rem]:block`} /> : null}
            </div>
          </div>
        </li>
      </ol>
      <div className="mt-4 flex max-w-4xl flex-col gap-2 border-t border-axis pt-4">
        <p role="status" data-question-sum="" className={`${LINE} font-semibold text-ink`}>
          {copy.sum(editable ? judged.sum : set.sum)}
        </p>
        <p role="status" data-question-warning="" className={`${LINE} text-ink`}>
          {editable && judged.quantityOut ? copy.quantityWarning : ""}
        </p>
      </div>
      {editable ? (
        <div className="mt-4 flex flex-col items-start gap-3">
          <Button
            variant="secondary"
            unavailable={save.isPending || blocked}
            onClick={() => {
              if (save.isPending || judged.body === null || judged.sum !== 100) return;
              setSaved(false);
              save.mutate(judged.body);
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

function QuestionRow({
  item,
  idBase,
  editable,
  excluded,
  value,
  error,
  onChange,
  onLeave,
  onToggle,
}: {
  item: QuestionItem;
  idBase: string;
  editable: boolean;
  excluded: boolean;
  value: string;
  error: string | undefined;
  onChange: (value: string) => void;
  onLeave: () => void;
  onToggle: () => void;
}) {
  const titleId = `${idBase}-title`;
  const meta = [copy.types[item.type] ?? item.type, item.starting_task ? copy.startingTask : null, item.quantity ? copy.quantity : null]
    .filter(Boolean)
    .join(" · ");
  return (
    <li data-question={item.id} data-excluded={excluded ? "" : undefined} className="border-t border-axis py-4">
      <div className={ROW}>
        <div className="min-w-0">
          <p id={titleId} className={`${LINE} font-semibold ${excluded ? "text-ink-secondary" : "text-ink"}`}>
            {item.title}
          </p>
          <p className="mt-1 text-body-phone text-ink-secondary">{meta}</p>
        </div>
        <div className={CONTROLS}>
          {excluded ? (
            <p className={`${LINE} ${FIELD} flex min-h-control-height-phone items-center font-semibold text-ink`}>
              {copy.takenOut}
            </p>
          ) : editable ? (
            <TextField
              id={`${idBase}-weight`}
              label={copy.weight}
              aria-labelledby={`${titleId} ${idBase}-weight-label`}
              inputMode="numeric"
              className={FIELD}
              value={value}
              error={error}
              onChange={(event) => onChange(event.target.value)}
              onBlur={onLeave}
            />
          ) : (
            <p className={`${LINE} ${FIELD} text-ink`}>{copy.weightText(item.weight)}</p>
          )}
          {editable ? (
            <Button variant="secondary" className={TOGGLE} aria-describedby={titleId} onClick={onToggle}>
              {excluded ? copy.putBack : copy.takeOut}
            </Button>
          ) : null}
        </div>
      </div>
    </li>
  );
}
