"use client";

import { nb } from "@/copy/nb";
import { useLive } from "@/lib/api/live";
import { formatClock, useConnection } from "@/lib/connection";

/**
 * Tilkoblingslinje (`connection-notice`, DESIGN.md → Components → System, UX-DR58, UX-DR59).
 * One line of `ink` text between two 1 px `ink-muted` rules at the top of the content, in the
 * page's flow, so it never covers a control. An optional «Prøv igjen» at its right and an
 * optional `ink-secondary` «Sist oppdatert 21:14». No fill, no icon, nothing moves.
 *
 * The polite status region is always rendered, so a line that appears is announced.
 */
export function ConnectionNotice({
  message,
  onRetry,
  action,
  updatedAt,
}: {
  message?: string;
  onRetry?: () => void;
  /** Another action than «Prøv igjen» at the line's right («Last inn på nytt»). */
  action?: LineAction;
  updatedAt?: number;
}) {
  const act = action ?? (onRetry ? { label: nb.system.retry, onPress: onRetry } : undefined);
  return (
    <div role="status" data-connection-notice="">
      {message ? (
        <div className="mb-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-y border-ink-muted py-2">
          <p className="text-body-phone text-ink lg:text-body">
            {message}
            {updatedAt ? (
              <>
                {" "}
                <span className="text-ink-secondary">{nb.system.lastUpdated(formatClock(updatedAt))}</span>
              </>
            ) : null}
          </p>
          {act ? (
            // A button that looks like a Lenke: it reloads the page's data in place, so anything
            // typed stays, and a Lenke never acts.
            <button
              type="button"
              onClick={act.onPress}
              className="inline-flex min-h-tap-target-min cursor-pointer items-center text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink"
            >
              {act.label}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export type LineAction = { label: string; onPress: () => void };

/** A page's own wording for its live values (the Oversikt, Story 7.5): the stale line with its
 * action, and a line for a background read that failed while the page still shows the last one. */
export type LiveLines = {
  stale: (clock: string) => string;
  staleAction: LineAction;
  failed?: { message: string; action: LineAction };
};

/**
 * The Tilkoblingslinje a page shows: offline first, then a page error (with «Prøv igjen»), then
 * live values gone stale (no heartbeat from the event stream, Story 6.4) with the time they were
 * last known current, in the page's own `lines` when it gives them, then a failed background read
 * (`lines.failed`), then «Tilkoblet igjen.» for 5 s after the connection or the stream returns.
 * `updatedAt` is when the page's live values were last read; it shows while offline.
 */
export function ConnectionLine({
  pageError = false,
  onRetry,
  updatedAt,
  lines,
}: {
  pageError?: boolean;
  onRetry?: () => void;
  updatedAt?: number;
  lines?: LiveLines;
}) {
  const connection = useConnection();
  const live = useLive();
  if (connection === "offline") return <ConnectionNotice message={nb.system.offline} updatedAt={updatedAt} />;
  if (pageError) return <ConnectionNotice message={nb.system.pageError} onRetry={onRetry} />;
  if (live.status === "stale" && lines) {
    return <ConnectionNotice message={lines.stale(formatClock(live.lastBeat))} action={lines.staleAction} />;
  }
  if (live.status === "stale") return <ConnectionNotice message={nb.system.stale} updatedAt={live.lastBeat} />;
  if (lines?.failed) return <ConnectionNotice message={lines.failed.message} action={lines.failed.action} />;
  if (connection === "reconnected" || live.recovered) return <ConnectionNotice message={nb.system.reconnected} />;
  return <ConnectionNotice />;
}
