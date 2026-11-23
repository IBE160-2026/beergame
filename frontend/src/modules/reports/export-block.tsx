"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { osloDateText } from "@/modules/sessions/dates";

import {
  completionExportPath,
  gameDataExportPath,
  reportsZipFilePath,
  reportsZipKey,
  requestReportsZip,
  useReportsZip,
  type ZipState,
} from "./api";

const copy = nb.reports.export;
const LINE = "text-body-phone text-ink lg:text-body";
/** The Lenke look (DESIGN.md → Controls) on a plain anchor: the download is an api route, not a
 * page, so Next's client navigation must not take it. */
const LINK =
  "inline-flex min-h-tap-target-min items-center text-label font-semibold text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

/** What the ZIP action shows for a state (pure, so it is tested without a browser). */
export type ZipView = "deleted" | "make" | "pending" | "ready" | "failed";

export function zipView(state: ZipState, pressed: boolean): ZipView {
  if (state.deleted) return "deleted";
  if (pressed || state.status === "pending") return "pending";
  if (state.status === "failed") return "failed";
  if (state.status === "ready") return "ready";
  return "make";
}

/**
 * The Klasseøkt's «Eksport» block (Story 13.13, FR-59, UX-DR49): «Last ned alle Studentrapporter
 * (ZIP)» asks the api to make one ZIP of every Student's report, never with the AI assessment.
 * While it is made the line says so; when the job ends the requester's `user` event reads the state
 * again, so the download appears without a reload, and the requester also gets a mail. The ZIP is
 * shared by the staff of the Class. A failed job reads «ZIP-filen kunne ikke lages.» with «Prøv
 * igjen». The status line is announced politely; focus stays where it was (UX-DR76). Shown only to
 * the staff the api lets read it: anyone else gets 403 and sees no block.
 *
 * Story 13.14 (FR-60): for the Lecturers of the Class (`completion_export`), «Last ned
 * fullføringsliste (CSV eller Excel)» opens the choice of a CSV or an Excel file, each a plain
 * download link, with the note «Ingen av filene har KI-vurderinger.». An Assistant lecturer sees
 * the report downloads only.
 *
 * Story 14.8 (FR-88, cut list): while `FEATURE_GAME_DATA_EXPORT` is on, the Lecturers of the Class
 * (`game_data_export`) also get «Last ned spilldata (CSV)», a plain download link. The note «Ingen av
 * filene har KI-vurderinger.» is said once under the Lecturers' files.
 */
export function ExportBlock({ sessionId }: { sessionId: string }) {
  const titleId = useId();
  const formatsId = useId();
  const [choosing, setChoosing] = useState(false);
  const queryClient = useQueryClient();
  const zip = useReportsZip(sessionId);
  const making = useAction({
    mutationFn: () => requestReportsZip(sessionId),
    messages: copy.zip.errors,
    fallback: copy.zip.failed,
    onSuccess: (state) => queryClient.setQueryData(reportsZipKey(sessionId), state),
  });
  // Refused (`data_deleted`, `no_students`): read the state again, so the block shows what holds.
  const refusedPress = making.isError;
  useEffect(() => {
    if (refusedPress) void queryClient.invalidateQueries({ queryKey: reportsZipKey(sessionId) });
  }, [refusedPress, queryClient, sessionId]);
  const state = zip.data;
  // The pending line is announced once the press was answered; «klar» once it turned ready here.
  const [announced, setAnnounced] = useState("");
  const previous = useRef<ZipState["status"] | undefined>(undefined);
  useEffect(() => {
    const status = state?.status;
    if (previous.current === "pending" && status === "ready") setAnnounced(copy.zip.ready);
    else if (status === "pending") setAnnounced(copy.zip.pending);
    else if (previous.current === "pending" && status === "failed") setAnnounced(copy.zip.failed);
    previous.current = status;
  }, [state?.status]);
  if (!state) {
    // Not staff of the Class (403): no block. Any other failure says so, instead of hiding it.
    const refused = zip.error instanceof ApiRequestError && zip.error.status === 403;
    return zip.isError && !refused ? (
      <section className="mt-12 border-t border-hairline pt-8" data-export="" data-export-zip="error">
        <h2 className="text-headline text-ink">{copy.title}</h2>
        <ActionError message={copy.zip.unread} />
      </section>
    ) : null;
  }
  const view = zipView(state, making.isPending);
  const press = () => {
    if (!making.isPending) making.mutate();
  };
  return (
    <section
      aria-labelledby={titleId}
      className="mt-12 border-t border-hairline pt-8"
      data-export=""
      data-export-zip={view}
    >
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      <p role="status" className="sr-only">
        {announced}
      </p>
      <div className="mt-3 flex max-w-2xl flex-col items-start gap-2">
        {view === "deleted" ? (
          <p className={LINE}>{copy.zip.deleted}</p>
        ) : (
          <>
            {/* The latest ZIP made stays downloadable while a new one is made or after one failed. */}
            {state.generated_at ? (
              <>
                <a href={reportsZipFilePath(sessionId)} className={LINK} download>
                  {copy.zip.action}
                </a>
                <p className={`${LINE} text-ink-secondary`}>
                  {copy.zip.made(osloDateText(state.generated_at), state.students ?? 0)}
                </p>
              </>
            ) : null}
            {view === "pending" ? (
              <p className={LINE} aria-hidden="true">
                {copy.zip.pending}
              </p>
            ) : null}
            {view === "failed" ? <ActionError message={copy.zip.failed} /> : null}
            {view === "make" ? (
              <Button variant="secondary" onClick={press}>
                {copy.zip.action}
              </Button>
            ) : view === "ready" || view === "failed" ? (
              <Button variant="secondary" onClick={press}>
                {view === "failed" ? copy.zip.retry : copy.zip.again}
              </Button>
            ) : null}
            <p className={`${LINE} text-ink-secondary`}>{copy.zip.note}</p>
          </>
        )}
        <ActionError message={making.errorMessage} />
      </div>
      {(state.completion_export || state.game_data_export) && !state.deleted ? (
        <div className="mt-8 flex max-w-2xl flex-col items-start gap-2" data-export-files="">
          {state.completion_export ? (
            <div className="flex flex-col items-start gap-2" data-export-completion="">
              <Button
                variant="secondary"
                aria-expanded={choosing}
                aria-controls={formatsId}
                onClick={() => setChoosing((open) => !open)}
              >
                {copy.completion.action}
              </Button>
              <div id={formatsId} hidden={!choosing} className="flex flex-wrap items-center gap-x-6 gap-y-1">
                <span className={LINE}>{copy.completion.choose}</span>
                <a href={completionExportPath(sessionId, "csv")} className={`${LINK} min-w-tap-target-min`} download>
                  {copy.completion.csv}
                </a>
                <a href={completionExportPath(sessionId, "xlsx")} className={`${LINK} min-w-tap-target-min`} download>
                  {copy.completion.xlsx}
                </a>
              </div>
            </div>
          ) : null}
          {state.game_data_export ? (
            <a
              href={gameDataExportPath(sessionId)}
              className={`${LINK} min-w-tap-target-min`}
              download
              data-export-game-data=""
            >
              {copy.gameData.action}
            </a>
          ) : null}
          <p className={`${LINE} text-ink-secondary`}>{copy.completion.note}</p>
        </div>
      ) : null}
    </section>
  );
}
