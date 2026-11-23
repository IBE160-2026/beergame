"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Switch } from "@/components/switch";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useAction } from "@/lib/api/mutation";
import { osloDateText } from "@/modules/sessions/dates";

import {
  myReportFilePath,
  myReportKey,
  myReportsKey,
  requestMyReport,
  type ReportState,
  useMyReport,
} from "./api";

const copy = nb.reports.download;
const LINE = "text-body-phone text-ink lg:text-body";
/** The Lenke look (DESIGN.md → Controls) on a plain anchor: the download is an api route, not a
 * page, so Next's client navigation must not take it. */
const LINK =
  "inline-flex min-h-tap-target-min items-center text-label font-semibold text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

/** What the download shows for a state (pure, so it is tested without a browser). */
export type DownloadView =
  | { kind: "closed"; opensAt: string | null }
  | { kind: "make" }
  | { kind: "pending" }
  | { kind: "ready" }
  | { kind: "failed" };

export function downloadView(
  state: ReportState,
  pressed: boolean,
): DownloadView {
  if (!state.open) return { kind: "closed", opensAt: state.opens_at };
  if (pressed || state.status === "pending") return { kind: "pending" };
  if (state.status === "failed") return { kind: "failed" };
  if (state.status === "ready") return { kind: "ready" };
  return { kind: "make" };
}

/**
 * The Student report's download (Story 13.7, FR-57, UX-DR29): under the «Rapport» step on Hjem, and
 * from Story 15.1 at the top of «Mine data». «Lag Studentrapport» asks the api to make the PDF
 * (it takes up to half a minute); while it is made the line says so, and when the render ends the
 * Student's `user` event reads the state again, so «Last ned Studentrapporten (PDF)» appears without
 * a reload. The Lenke goes to the api, which checks the policy and sends a signed URL. A failed
 * render shows the error inline with «Prøv igjen». Every new press makes a new PDF, so a later
 * correction shows. Before the Testfrist it says when it opens. The status line is announced
 * politely; focus stays on the button (UX-DR76).
 *
 * Story 13.11 (FR-58, FR-61): while the Student's AI assessment is ready, a Bryter «KI-vurdering i
 * rapporten», off on every visit, adds the AI assessment section. Each choice is a report of its
 * own: the state, the press and the link follow the Bryter, so the standard link never serves the
 * PDF with the section. Not ready, switched off or failed: no Bryter, the standard report only.
 */
export function ReportDownload({ sessionId }: { sessionId: string }) {
  const queryClient = useQueryClient();
  const ids = useId();
  const [withAi, setWithAi] = useState(false);
  const standard = useMyReport(sessionId);
  const available = standard.data?.ai_available === true;
  const ai = withAi && available;
  // Read only once the Student turns the Bryter on.
  const added = useMyReport(sessionId, true, ai);
  const report = ai ? added : standard;
  const making = useAction({
    mutationFn: (asked: boolean) => requestMyReport(sessionId, asked),
    messages: copy.errors,
    fallback: copy.failed,
    onSuccess: (state, asked) =>
      queryClient.setQueryData(myReportKey(sessionId, asked), state),
  });
  const base = standard.data;
  // While the AI variant's state is read, only the Bryter shows (it stays, with focus on it).
  const state = report.data;
  // Refused as unavailable (the assessment changed meanwhile): read the state again, so the
  // Bryter goes and the standard report shows.
  const refused =
    making.error instanceof ApiRequestError &&
    making.error.code === "ai_assessment_unavailable";
  useEffect(() => {
    if (refused) void queryClient.invalidateQueries({ queryKey: myReportsKey });
  }, [refused, queryClient]);
  // The pending line is announced once the press was answered; «klar» once it turned ready here.
  const [announced, setAnnounced] = useState("");
  const previous = useRef<ReportState["status"] | undefined>(undefined);
  useEffect(() => {
    const status = state?.status;
    if (previous.current === "pending" && status === "ready")
      setAnnounced(copy.ready);
    else if (status === "pending") setAnnounced(copy.pending);
    previous.current = status;
  }, [state?.status]);
  if (!base) return null;
  const view = state ? downloadView(state, making.isPending) : null;
  const press = () => making.mutate(ai);
  const nameId = `${ids}-ai`;
  const helpId = `${ids}-ai-help`;
  return (
    <div
      className="mt-2 flex flex-col items-start gap-2"
      data-report-download={view?.kind ?? "loading"}
    >
      <p role="status" className="sr-only">
        {announced}
      </p>
      {available && base.open ? (
        <div
          className="flex flex-col items-start gap-1"
          data-report-ai={ai ? "on" : "off"}
        >
          <p id={nameId} className={`${LINE} font-semibold`}>
            {copy.ai.control}
          </p>
          <Switch
            id={`${ids}-ai-switch`}
            checked={ai}
            labelledBy={nameId}
            describedBy={helpId}
            onChange={(on) => {
              if (!making.isPending) setWithAi(on);
            }}
          >
            {ai ? copy.ai.on : copy.ai.off}
          </Switch>
          <p id={helpId} className={`${LINE} text-ink-secondary`}>
            {copy.ai.help}
          </p>
        </div>
      ) : null}
      {state && view ? (
        <>
          {view.kind === "closed" ? (
            view.opensAt ? (
              <p className={`${LINE} text-ink-secondary`}>
                {copy.opens(osloDateText(view.opensAt))}
              </p>
            ) : null
          ) : null}
          {view.kind === "pending" ? (
            <p className={LINE} aria-hidden="true">
              {copy.pending}
            </p>
          ) : null}
          {/* The latest PDF made stays downloadable while a new one is made or after one failed. */}
          {state.open && state.generated_at ? (
            <>
              <a
                href={myReportFilePath(sessionId, state.ai)}
                className={LINK}
                download
              >
                {copy.link}
              </a>
              <p className={`${LINE} text-ink-secondary`}>
                {copy.made(osloDateText(state.generated_at))}
              </p>
            </>
          ) : null}
          {view.kind === "failed" ? (
            <ActionError message={copy.failed} />
          ) : null}
          {view.kind === "make" ||
          view.kind === "ready" ||
          view.kind === "failed" ? (
            <>
              <Button variant="secondary" onClick={press}>
                {view.kind === "failed"
                  ? copy.retry
                  : view.kind === "ready"
                    ? copy.again
                    : copy.make}
              </Button>
              <p className={`${LINE} text-ink-secondary`}>{copy.note}</p>
            </>
          ) : null}
        </>
      ) : report.isError ? (
        <ActionError message={copy.failed} />
      ) : null}
      <ActionError message={making.errorMessage} />
    </div>
  );
}
