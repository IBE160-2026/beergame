"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SelectField } from "@/components/select-field";
import { Skeleton } from "@/components/skeleton";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { errorCode, useAction } from "@/lib/api/mutation";
import { cn } from "@/lib/utils";

import {
  chooseRosterColumn,
  classesKey,
  classKey,
  deleteRosterUpload,
  pasteRoster,
  type RosterSent,
  type RosterStaging,
  type RosterUpload as Staged,
  invitationSummaryKey,
  registrationsKey,
  rosterUploadKey,
  sendRosterInvitations,
  uploadRoster,
  useRosterUpload,
} from "./api";
import {
  columnHasNoAddress,
  columnLabel,
  columnReason,
  dayLabel,
  invalidReason,
  invalidValueLabel,
  parseValidDays,
  VALID_DAYS,
} from "./roster";
import { useFormArea } from "./one-form";
import { EntryResult, ManualForm, resultText } from "./roster-entry-forms";

const copy = nb.classes.roster;

/** The types the file picker offers; the api decides by the name and the content. */
const ACCEPT = ".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv";

const LINK_BUTTON =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center self-start text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

/**
 * Filopplasting on the Class page (Stories 4.2 and 4.3, FR-7, UX-DR47). Story 4.3 adds the
 * invalid-row list, «Send N Invitasjoner» and sending pasted addresses, which are staged as a
 * one-column list with no column select or preview. Story 4.4 makes «Send N Invitasjoner» send,
 * with a validity in whole days; the result line then stands above an empty box. Before a file is chosen: an outlined
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
  const resultLine = useRef<HTMLParagraphElement>(null);
  const sentLine = useRef<HTMLParagraphElement>(null);
  const [sent, setSent] = useState<RosterSent | null>(null);
  const [pasting, setPasting] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [pending, setPending] = useState<number | null>(null);
  const latestColumn = useRef<number | null>(null);
  // Where focus goes once the box has been drawn again: an element that is about to appear
  // cannot take it in the handler that makes it appear.
  const [focusNext, setFocusNext] = useState<"choose" | "column" | "paste" | "result" | "sent" | null>(null);
  useEffect(() => {
    if (!focusNext) return;
    const target = {
      choose: chooseButton,
      column: columnSelect,
      paste: pasteField,
      result: resultLine,
      sent: sentLine,
    }[focusNext].current;
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
  const paste = useAction({
    mutationFn: (text: string) => pasteRoster(classId, text),
    messages: { roster_paste_too_long: copy.pasteTooLong, invalid_request: copy.pasteTooLong },
    fallback: copy.pasteFailed,
    onSuccess: (staged) => {
      // A column answer still on its way belongs to the replaced file: it no longer counts.
      latestColumn.current = null;
      setPending(null);
      store(staged);
      setPasting(false);
      setPasteText("");
      setFocusNext("result");
    },
  });
  const send = useAction({
    mutationFn: ({ uploadId, days }: { uploadId: string; days: number }) =>
      sendRosterInvitations(classId, uploadId, days),
    messages: {
      not_found: copy.sendGone,
      nothing_to_send: copy.nothingToSend,
      processing_agreement_missing: nb.classes.processingAgreementMissing,
      invalid_request: copy.validDaysError(VALID_DAYS.min, VALID_DAYS.max),
    },
    fallback: copy.sendFailed,
    onSuccess: (result) => {
      latestColumn.current = null;
      setPending(null);
      store(null);
      setSent(result);
      setFocusNext("sent");
      void queryClient.invalidateQueries({ queryKey: classKey(classId), exact: true });
      void queryClient.invalidateQueries({ queryKey: classesKey, exact: true });
      void queryClient.invalidateQueries({ queryKey: invitationSummaryKey(classId), exact: true });
      void queryClient.invalidateQueries({ queryKey: registrationsKey(classId), exact: true });
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
    send.reset();
    setSent(null);
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
    paste.reset();
    send.reset();
    setSent(null);
    setPasting(true);
    setFocusNext("paste");
  };

  const endPaste = () => {
    if (paste.isPending) return; // the addresses being read would be staged out of sight
    paste.reset();
    setPasting(false);
    const current = staging.data?.upload;
    setFocusNext(current ? (current.source === "file" ? "column" : "result") : "choose");
  };

  if (pasting) {
    return (
      <div className="flex max-w-md flex-col gap-field-gap">
        <label htmlFor="roster-paste" className="text-label text-ink">
          {copy.pasteLabel}
        </label>
        <textarea
          id="roster-paste"
          rows={6}
          aria-describedby={paste.errorMessage ? "roster-paste-hint roster-paste-error" : "roster-paste-hint"}
          aria-invalid={paste.errorMessage ? true : undefined}
          ref={pasteField}
          value={pasteText}
          onChange={(event) => {
            setPasteText(event.target.value);
            if (paste.isError) paste.reset(); // the refusal clears as the user types
          }}
          className="w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre"
        />
        <p id="roster-paste-hint" className="text-body-phone text-ink-secondary">
          {copy.pasteHint}
        </p>
        {paste.errorMessage ? (
          <p id="roster-paste-error" role="alert" className="text-body-phone text-restordre">
            {paste.errorMessage}
          </p>
        ) : null}
        <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-2">
          <Button unavailable={paste.isPending} onClick={() => paste.mutate(pasteText)}>
            {copy.pasteContinue}
          </Button>
          <button type="button" className={cn(LINK_BUTTON, "self-center")} onClick={endPaste}>
            {copy.fileInstead}
          </button>
        </div>
      </div>
    );
  }

  const shown = staged ? (pending ?? staged.chosen_column) : null;
  const fromFile = staged?.source === "file";
  const noAddress = staged !== null && fromFile && columnHasNoAddress(staged);

  return (
    // Side by side when both fit (the mockup at 1440 px); the preview wraps under the controls
    // when they do not, at 320 px and at 200 % text.
    <div className="flex flex-wrap gap-x-16 gap-y-10">
      <div className="flex min-w-0 max-w-full shrink grow-0 basis-md flex-col gap-6">
        {sent ? (
          <p
            ref={sentLine}
            tabIndex={-1}
            role="status"
            className="text-body-phone text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink lg:text-body"
          >
            {copy.sent(sent.sent, dayLabel(sent.last_valid_day, todayIso()))}
          </p>
        ) : null}
        <div className="flex flex-col gap-field-gap">
          <p id="roster-file-label" className="text-label text-ink">
            {staged && !fromFile ? copy.pasteLabel : copy.fileLabel}
          </p>
          {staged ? (
            <div
              role="group"
              aria-labelledby="roster-file-label"
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-sm border border-axis bg-future-tint px-4 py-3"
            >
              <div className="min-w-0">
                <p className="text-label text-ink [overflow-wrap:anywhere]">
                  {fromFile ? staged.file_name : copy.pasted}
                </p>
                <p
                  ref={resultLine}
                  tabIndex={-1}
                  role="status"
                  className="text-body-phone text-ink-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
                >
                  {fromFile ? copy.rowsRead(staged.row_count) : copy.addressesRead(staged.row_count)}
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
                  send.reset();
                  latestColumn.current = null;
                  setPending(null);
                  discard.mutate();
                }}
              >
                {fromFile ? copy.changeFile : copy.startOver}
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

        {staged && fromFile ? (
          <div className="flex flex-col gap-2">
            <SelectField
              id="roster-column"
              ref={columnSelect}
              label={copy.emailColumn}
              value={shown === null ? "" : String(shown)}
              onChange={onColumn}
              hint={noAddress ? undefined : columnReason(staged)}
              error={noAddress ? columnReason(staged) : undefined}
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

        {staged ? (
          <SendArea
            staged={staged}
            sending={send.isPending}
            onEdit={() => {
              if (send.isError) send.reset();
            }}
            onSend={(days) => {
              setSent(null);
              send.mutate(
                { uploadId: staged.id, days },
                {
                  onError: (error) => {
                    // The staging changed under the page: show the one the api has now.
                    const code = errorCode(error);
                    if (code === "not_found" || code === "nothing_to_send") void staging.refetch();
                  },
                },
              );
            }}
          />
        ) : null}
        {/* Outside the send area: a refused send whose staging is gone keeps its line. */}
        <ActionError message={send.errorMessage} />
      </div>

      {staged ? (
        <div className="flex min-w-0 max-w-full shrink grow basis-sm flex-col gap-10">
          <InvalidRows classId={classId} staged={staged} />
          {fromFile ? <Preview staged={staged} chosen={shown} /> : null}
        </div>
      ) : null}
    </div>
  );
}

/** Today as an ISO date on the browser's clock, for the year in the result line. */
function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

/** «Gyldig i antall dager», prefilled with 14, and «Send N Invitasjoner» with the number of rows
 * that get one (Story 4.4, FR-8, UX-DR47). A validity that is not a whole number of days in the
 * range is refused under the field before anything is sent, and the line clears as the Lecturer
 * types. Unavailable, still primary, when no row is valid, and the page says so (UX-DR9).
 * «Ugyldige rader får ingen e-post …» stands by the button only once rows are staged (Issue #86). */
function SendArea({
  staged,
  sending,
  onEdit,
  onSend,
}: {
  staged: Staged;
  sending: boolean;
  onEdit: () => void;
  onSend: (days: number) => void;
}) {
  const [days, setDays] = useState(String(VALID_DAYS.default));
  const [refused, setRefused] = useState(false);
  const none = staged.valid_count === 0;
  const note = staged.row_count > 0;
  // A removed, registered Student sent again is put back with access and no Invitation (Story
  // 4.8): the button counts only the Invitations that go out (Issue #91).
  const restored = staged.restored_count;
  const invites = staged.valid_count - restored;
  const described = [none ? "roster-send-none" : "", restored > 0 ? "roster-send-restored" : "", note ? "roster-send-note" : ""]
    .filter(Boolean)
    .join(" ");
  return (
    <form
      noValidate
      className="flex flex-col items-start gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (none || sending) return;
        const parsed = parseValidDays(days);
        if (parsed === null) {
          setRefused(true);
          return;
        }
        onSend(parsed);
      }}
    >
      {none ? null : (
        <TextField
          id="roster-valid-days"
          label={copy.validDays}
          inputMode="numeric"
          autoComplete="off"
          value={days}
          onChange={(event) => {
            setDays(event.target.value);
            setRefused(false);
            onEdit();
          }}
          hint={copy.validDaysHint(VALID_DAYS.min, VALID_DAYS.max)}
          error={refused ? copy.validDaysError(VALID_DAYS.min, VALID_DAYS.max) : undefined}
          // The field fits a number of days; its hint and error keep the send area's width.
          className="w-full max-w-md"
          inputClassName="max-w-[14rem]"
        />
      )}
      <Button
        type="submit"
        variant="primary"
        unavailable={none || sending}
        aria-describedby={described || undefined}
        className="w-full max-w-md"
      >
        {sending ? copy.sending : invites === 0 && restored > 0 ? copy.restoreOnly : copy.send(invites)}
      </Button>
      {none ? (
        <p id="roster-send-none" className="text-body-phone text-ink">
          {copy.noValid}
        </p>
      ) : null}
      {restored > 0 ? (
        <p id="roster-send-restored" className="max-w-md text-body-phone text-ink-secondary">
          {copy.restoredNote(restored)}
        </p>
      ) : null}
      {note ? (
        <p id="roster-send-note" className="max-w-md text-body-phone text-ink-secondary">
          {copy.invalidNote}
        </p>
      ) : null}
    </form>
  );
}

/** How many invalid rows the page lists; the heading still counts them all. */
const INVALID_ROWS_SHOWN = 100;

/** «Ugyldige rader: 4 av 250» and one line per row that gets no Invitation: its number, its
 * value and its reason in text, never colour alone (Story 4.3, FR-7, NFR-6). The lines stack at
 * 320 px. Pasted addresses are named by their place in the text, not as file rows. At most
 * `INVALID_ROWS_SHOWN` lines are drawn. «Registrer manuelt» opens the form in place under its row,
 * prefilled with the row's value (Story 4.8); a registration deletes the staged row it corrected.
 * Nothing shows when every row is valid or no column is chosen. */
function InvalidRows({ classId, staged }: { classId: string; staged: Staged }) {
  const [open, setOpen] = useState<number | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const resultLine = useRef<HTMLParagraphElement>(null);
  const [focusResult, setFocusResult] = useState(false);
  useEffect(() => {
    if (focusResult && resultLine.current) {
      resultLine.current.focus();
      setFocusResult(false);
    }
  }, [focusResult, result]);
  // Another area's form closes this one and clears its result line (one form on the page).
  const take = useFormArea("invalid-rows", () => {
    setOpen(null);
    setResult(null);
  });
  if (staged.invalid_rows.length === 0 && !result) return null;
  const pasted = staged.source === "paste";
  const rowWord = pasted ? copy.invalidPlace : copy.invalidRow;
  const valueWord = invalidValueLabel(staged);
  const shown = staged.invalid_rows.slice(0, INVALID_ROWS_SHOWN);
  const grid = "sm:grid sm:grid-cols-[3.5rem_minmax(0,1fr)_minmax(0,11rem)_8.5rem] sm:items-center sm:gap-x-4";
  return (
    <section aria-labelledby={staged.invalid_rows.length > 0 ? "roster-invalid-title" : undefined} className="min-w-0">
      {result ? <EntryResult text={result} ref={resultLine} /> : null}
      {staged.invalid_rows.length > 0 ? (
        <>
          <h3 id="roster-invalid-title" className={cn("text-step-title text-ink", result && "mt-6")}>
            {copy.invalidTitle(staged.invalid_rows.length, staged.row_count)}
          </h3>
          <div aria-hidden="true" className={cn("mt-3 hidden border-b border-axis py-2 text-label text-ink", grid)}>
            <span>{rowWord}</span>
            <span>{valueWord}</span>
            <span>{copy.invalidReason}</span>
            <span />
          </div>
          <ul className="mt-3 sm:mt-0">
            {shown.map((row) => (
              <li key={row.row_number} className="border-b border-hairline">
                <div
                  className={cn(
                    // In the grid the 44 px «Registrer manuelt» sets the height; mockup 02 rows are about 54 px.
                    "relative flex flex-col gap-1 py-3 text-body-phone text-ink sm:py-1 lg:text-body",
                    grid,
                  )}
                >
                  <span className="tabular-nums text-label">
                    <span className="sm:sr-only">{rowWord} </span>
                    {row.row_number}
                  </span>
                  <span className="min-w-0 [overflow-wrap:anywhere]">
                    <span className="sr-only">{valueWord}: </span>
                    {row.value}
                  </span>
                  <span className="text-restordre">
                    <span className="sr-only">{copy.invalidReason}: </span>
                    {invalidReason(row)}
                  </span>
                  <button
                    type="button"
                    className={cn(LINK_BUTTON, "self-start sm:self-center")}
                    aria-label={`${copy.registerManually}, ${rowWord.toLowerCase()} ${row.row_number}`}
                    aria-expanded={open === row.row_number}
                    onClick={(event) => {
                      opener.current = event.currentTarget;
                      setResult(null); // a new action clears the last result line
                      setOpen(row.row_number);
                      take();
                    }}
                  >
                    {copy.registerManually}
                  </button>
                </div>
                {open === row.row_number ? (
                  <div className="mb-3">
                    <ManualForm
                      classId={classId}
                      from={{
                        email: row.value.trim(),
                        uploadRow: { upload_id: staged.id, row_number: row.row_number },
                      }}
                      idPrefix={`roster-row-${row.row_number}`}
                      onDone={(registration) => {
                        setOpen(null);
                        setResult(resultText("manual", registration));
                        setFocusResult(true);
                      }}
                      onCancel={() => {
                        setOpen(null);
                        opener.current?.focus();
                      }}
                    />
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
          {staged.invalid_rows.length > shown.length ? (
            <p className="mt-3 text-body-phone text-ink-secondary">
              {copy.invalidShown(shown.length, staged.invalid_rows.length)}
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

/** «Forhåndsvisning av fila»: the first rows as the api staged them, the chosen column tinted and
 * named as chosen to screen readers only (mockup 02 has no visible suffix). Wide files scroll
 * inside the table's own region, never the page, with «Rad» kept in view (DESIGN.md: sticky labels), and the region brings the chosen column into view,
 * so at 320 px the column the selector names is the one on screen. */
function Preview({ staged, chosen }: { staged: Staged; chosen: number | null }) {
  const region = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const box = region.current;
    if (!box || chosen === null) return;
    const cell = box.querySelector<HTMLElement>(`th[data-column="${chosen}"]`);
    if (!cell) return;
    const label = box.querySelector<HTMLElement>("th[data-row-label]");
    const covered = label ? label.getBoundingClientRect().width : 0;
    const view = box.getBoundingClientRect();
    const rect = cell.getBoundingClientRect();
    // A column out of view is brought in with its left edge next to «Rad»; the columns after it
    // run off the right edge, which shows that the region scrolls.
    if (rect.left < view.left + covered || rect.right > view.right) {
      box.scrollLeft += rect.left - view.left - covered;
    }
  }, [chosen, staged]);
  return (
    <section aria-labelledby="roster-preview-title" className="min-w-0 max-w-full shrink grow basis-sm">
      <h3 id="roster-preview-title" className="text-step-title text-ink">
        {copy.preview}
      </h3>
      <p className="mt-1 text-body-phone text-ink-secondary">
        {copy.previewNote(staged.preview.length, staged.row_count)}
      </p>
      <div
        ref={region}
        role="region"
        aria-labelledby="roster-preview-title"
        tabIndex={0}
        className="mt-3 max-w-full overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        <table className="w-full border-collapse text-left text-body-phone text-ink lg:text-body">
          <thead>
            <tr className="border-b border-axis">
              <th scope="col" data-row-label className="sticky left-0 z-10 bg-paper py-2 pr-4 text-label text-ink">
                {copy.previewRow}
              </th>
              {staged.columns.map((c) => (
                <th
                  key={c.index}
                  scope="col"
                  data-column={c.index}
                  className={cn(
                    "relative whitespace-nowrap px-3 py-2 text-label text-ink",
                    c.index === chosen && "bg-future-tint",
                  )}
                >
                  <span className="text-ink-secondary">{c.letter}</span> {c.header}
                  {c.index === chosen ? <span className="sr-only">, {copy.previewChosen}</span> : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {staged.preview.map((row) => (
              <tr key={row.row_number} className="border-b border-hairline">
                <td className="sticky left-0 bg-paper py-2 pr-4 tabular-nums text-ink-secondary">{row.row_number}</td>
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
