"use client";

import { nb } from "@/copy/nb";
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
  updatedAt,
}: {
  message?: string;
  onRetry?: () => void;
  updatedAt?: number;
}) {
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
          {onRetry ? (
            // A button that looks like a Lenke: it reloads the page's data in place, so anything
            // typed stays, and a Lenke never acts.
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex min-h-tap-target-min cursor-pointer items-center text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink"
            >
              {nb.system.retry}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/**
 * The Tilkoblingslinje a page shows: offline first, then a page error (with «Prøv igjen»), then
 * «Tilkoblet igjen.» for 5 s after the connection returns. `updatedAt` is when the page's live
 * values were last read; it shows while offline.
 */
export function ConnectionLine({
  pageError = false,
  onRetry,
  updatedAt,
}: {
  pageError?: boolean;
  onRetry?: () => void;
  updatedAt?: number;
}) {
  const connection = useConnection();
  if (connection === "offline") return <ConnectionNotice message={nb.system.offline} updatedAt={updatedAt} />;
  if (pageError) return <ConnectionNotice message={nb.system.pageError} onRetry={onRetry} />;
  if (connection === "reconnected") return <ConnectionNotice message={nb.system.reconnected} />;
  return <ConnectionNotice />;
}
