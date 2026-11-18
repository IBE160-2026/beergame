"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SelectField } from "@/components/select-field";
import { Skeleton } from "@/components/skeleton";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";

import {
  chooseRosterColumn,
  deleteRosterUpload,
  type RosterStaging,
  type RosterUpload as Staged,
  rosterUploadKey,
  uploadRoster,
  useRosterUpload,
} from "./api";
import { columnLabel, columnReason } from "./roster";

const copy = nb.classes.roster;

/** The types the file picker offers; the api decides by the name and the content. */
const ACCEPT = ".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";

const LINK_BUTTON =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center self-start text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

/**
 * Filopplasting on the Class page (Story 4.2, FR-7, UX-DR47). Before a file is chosen: an outlined
 * box with «Velg fil» and the link «Lim inn adresser i stedet». After the api has read the file:
 * its name, «N rader lest» and «Bytt fil», then «E-postkolonne» with every column by letter and
 * header, the preselected one with its reason, and the first rows of the file. Choosing another
 * column has the api evaluate the staged rows again; «Bytt fil» deletes the staged upload. The
 * file goes to the api as it is and is never kept; the page shows only what the api answers.
 */
export function RosterUpload({ classId }: { classId: string }) {
  const queryClient = useQueryClient();
  const staging = useRosterUpload(classId);
  const fileInput = useRef<HTMLInputElement>(null);
  const chooseButton = useRef<HTMLButtonElement>(null);
  const columnSelect = useRef<HTMLSelectElement>(null);
  const pasteField = useRef<HTMLTextAreaElement>(null);
  const [pasting, setPasting] = useState(false);
  const [pending, setPending] = useState<number | null>(null);
  const latestColumn = useRef<number | null>(null);
  // Where focus goes once the box has been drawn again: an element that is about to appear
  // cannot take it in the handler that makes it appear.
  const [focusNext, setFocusNext] = useState<"choose" | "column" | "paste" | null>(null);
  useEffect(() => {
    if (!focusNext) return;
    const target = { choose: chooseButton, column: columnSelect, paste: pasteField }[focusNext].current;
    if (target) {
      target.focus();
      setFocusNext(null);
    }
  });

  const store = (upload: Staged | null) =>
    queryClient.setQueryData<RosterStaging>(rosterUploadKey(classId), { upload });

  const upload = useAction({
    mutationFn: (file: File) => uploadRoster(classId, file),
    messages: { roster_unreadable: copy.unreadable },
    fallback: copy.uploadFailed,
    onSuccess: (staged) => {
      store(staged);
      setFocusNext("column");
    },
  });
  const column = useAction({
    mutationFn: (index: number) => chooseRosterColumn(classId, index),
    fallback: copy.columnFailed,
    // Only the answer to the latest choice counts: earlier ones may arrive after it, and none
    // counts once «Bytt fil» has been pressed.
    onSuccess: (staged, index) => {
      if (latestColumn.current === index) store(staged);
    },
  });
  const discard = useAction({
    mutationFn: () => deleteRosterUpload(classId),
    fallback: copy.changeFailed,
    onSuccess: () => {
      store(null);
      setFocusNext("choose");
    },
  });

  if (staging.isPending) return <Skeleton heading={false} rows={2} />;
  if (staging.isError) {
    return (
      <div className="flex flex-col items-start gap-3">
        <p role="alert" className="text-body-phone text-restordre lg:text-body">
          {nb.system.pageError}
        </p>
        <Button onClick={() => void staging.refetch()}>{nb.system.retry}</Button>
      </div>
    );
  }
  const staged = staging.data.upload;

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // the same file can be chosen again after a refusal
    if (!file) return;
    column.reset();
    discard.reset();
    upload.mutate(file);
  };

  const onColumn = (event: ChangeEvent<HTMLSelectElement>) => {
    const index = Number(event.target.value);
    latestColumn.current = index;
    setPending(index);
    column.mutate(index, {
      onSettled: () => {
        if (latestColumn.current === index) setPending(null);
      },
    });
  };

  const startPaste = () => {
    if (upload.isPending) return; // the file being read would be staged out of sight
    upload.reset();
    setPasting(true);
    setFocusNext("paste");
  };

  const endPaste = () => {
    setPasting(false);
    setFocusNext(staging.data?.upload ? "column" : "choose");
  };

  if (pasting) {
    return (
      <div className="flex flex-col gap-field-gap">
        <label htmlFor="roster-paste" className="text-label text-ink">
          {copy.pasteLabel}
        </label>
        <textarea
          id="roster-paste"
          rows={6}
          aria-describedby="roster-paste-hint"
          ref={pasteField}
          className="w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink"
        />
        <p id="roster-paste-hint" className="text-body-phone text-ink-secondary">
          {copy.pasteHint}
        </p>
        <button type="button" className={LINK_BUTTON} onClick={endPaste}>
          {copy.fileInstead}
        </button>
      </div>
    );
  }

  const shown = staged ? (pending ?? staged.chosen_column) : null;

  return (
    // Side by side when both fit (the mockup at 1440 px); the preview wraps under the controls
    // when they do not, at 320 px and at 200 % text.
    <div className="flex flex-wrap gap-x-16 gap-y-10">
      <div className="flex min-w-0 max-w-full shrink grow-0 basis-md flex-col gap-6">
        <div className="flex flex-col gap-field-gap">
          <p id="roster-file-label" className="text-label text-ink">
            {copy.fileLabel}
          </p>
          {staged ? (
            <div
              role="group"
              aria-labelledby="roster-file-label"
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-sm border border-axis bg-future-tint px-4 py-3"
            >
              <div className="min-w-0">
                <p className="text-label text-ink [overflow-wrap:anywhere]">{staged.file_name}</p>
                <p role="status" className="text-body-phone text-ink-secondary">
                  {copy.rowsRead(staged.row_count)}
                </p>
              </div>
              <button
                type="button"
                className={LINK_BUTTON}
                aria-disabled={discard.isPending ? true : undefined}
                onClick={() => {
                  if (discard.isPending) return;
                  upload.reset();
                  column.reset();
                  latestColumn.current = null;
                  setPending(null);
                  discard.mutate();
                }}
              >
                {copy.changeFile}
              </button>
            </div>
          ) : (
            <div
              role="group"
              aria-labelledby="roster-file-label"
              aria-describedby="roster-file-accepts"
              className="flex flex-col items-start gap-3 rounded-sm border border-ink-muted px-4 py-4"
            >
              <input
                ref={fileInput}
                id="roster-file"
                type="file"
                accept={ACCEPT}
                hidden
                onChange={onFile}
                aria-hidden="true"
                tabIndex={-1}
              />
              <Button
                ref={chooseButton}
                unavailable={upload.isPending}
                onClick={() => fileInput.current?.click()}
              >
                {copy.chooseFile}
              </Button>
              <p id="roster-file-accepts" className="text-body-phone text-ink-secondary">
                {copy.accepts}
              </p>
              {upload.isPending ? (
                <p role="status" className="text-body-phone text-ink-secondary">
                  {copy.reading}
                </p>
              ) : null}
              <button type="button" className={LINK_BUTTON} onClick={startPaste}>
                {copy.pasteInstead}
              </button>
            </div>
          )}
          <ActionError message={upload.errorMessage ?? discard.errorMessage} />
        </div>

        {staged ? (
          <div className="flex flex-col gap-2">
            <SelectField
              id="roster-column"
              ref={columnSelect}
              label={copy.emailColumn}
              value={shown === null ? "" : String(shown)}
              onChange={onColumn}
              hint={columnReason(staged)}
            >
              {staged.chosen_column === null ? (
                <option value="" disabled>
                  {copy.chooseColumn}
                </option>
              ) : null}
              {staged.columns.map((c) => (
                <option key={c.index} value={c.index}>
                  {columnLabel(c)}
                </option>
              ))}
            </SelectField>
            <ActionError message={column.errorMessage} />
            {staged.chosen_column === null ? (
              <button type="button" className={LINK_BUTTON} onClick={startPaste}>
                {copy.pasteInstead}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      {staged ? <Preview staged={staged} chosen={shown} /> : null}
    </div>
  );
}

/** «Forhåndsvisning av fila»: the first rows as the api staged them, the chosen column marked in
 * its header text and tinted. Wide files scroll inside the table's own region, never the page. */
function Preview({ staged, chosen }: { staged: Staged; chosen: number | null }) {
  return (
    <section aria-labelledby="roster-preview-title" className="min-w-0 max-w-full shrink grow basis-sm">
      <h3 id="roster-preview-title" className="text-step-title text-ink">
        {copy.preview}
      </h3>
      <p className="mt-1 text-body-phone text-ink-secondary">
        {copy.previewNote(staged.preview.length, staged.row_count)}
      </p>
      <div
        role="region"
        aria-labelledby="roster-preview-title"
        tabIndex={0}
        className="mt-3 max-w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <table className="w-full border-collapse text-left text-body-phone text-ink lg:text-body">
          <thead>
            <tr className="border-b border-axis">
              <th scope="col" className="py-2 pr-4 text-label text-ink">
                {copy.previewRow}
              </th>
              {staged.columns.map((c) => (
                <th
                  key={c.index}
                  scope="col"
                  className={cn("whitespace-nowrap px-3 py-2 text-label text-ink", c.index === chosen && "bg-future-tint")}
                >
                  <span className="text-ink-secondary">{c.letter}</span> {c.header}
                  {c.index === chosen ? ` ${copy.previewChosen}` : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {staged.preview.map((row) => (
              <tr key={row.row_number} className="border-b border-hairline">
                <td className="py-2 pr-4 tabular-nums text-ink-secondary">{row.row_number}</td>
                {staged.columns.map((c) => (
                  <td
                    key={c.index}
                    className={cn("whitespace-nowrap px-3 py-2", c.index === chosen && "bg-future-tint")}
                  >
                    {row.cells[c.index] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
