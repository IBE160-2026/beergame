import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type SeatStatusState = "ordered" | "waiting";

export type SeatStatusRow = {
  key: string;
  /** The Role: «Fabrikk». */
  role: string;
  /** Who holds the Seat, in words: «Jonas», «Sara (deg)», «KI-spiller». */
  holder: string;
  /** A Student's name stands in `ink`; «KI-spiller», «ledig» and the like in `ink-secondary`. */
  named: boolean;
  /** Ordered (filled dot) or waiting (hollow dot); null draws no dot and no status (a game that
   * does not run). */
  state: SeatStatusState | null;
  /** The state in words, always: «har bestilt», «venter, 3 min», «venter», «venter (deg)». */
  status: string | null;
  /** Epic 8: a second line under the row (Takeover, Reclaim). Nothing in Epic 6. */
  detail?: ReactNode;
  /** Epic 8: an action under the row («Sett inn KI-spiller for Jonas»). Nothing in Epic 6. */
  action?: ReactNode;
};

/**
 * Setestatus (`seat-status-list`, DESIGN.md → Setestatus, EXPERIENCE.md → Setestatus, FR-25,
 * UX-DR25, Story 6.14): every Seat of the game as a row of dot, Role (weight 600), who holds it and
 * the status in words, right-aligned in `ink-secondary`. A filled dot means «har bestilt», a hollow
 * one waiting; the dot is decorative, the text always says the state. Rows reflow at any width.
 *
 * `announcement` is the polite «Venter på: Jonas (3 min) og deg.» line, read by screen readers
 * only: the list is always in view, so no such line is drawn (founder decision 2026-11-14). The
 * caller changes it only when whom the game waits for changes. Live updates never move focus.
 *
 * Named slots for Epic 8, empty in Epic 6: `statusLine` above the list (Pause, «I rommet»),
 * `controls` below it («Ta pause»), and each row's `detail` and `action`. The component holds no
 * rule about the game; the caller passes the words. Reused by Epics 7 and 8.
 */
export function SeatStatus({
  title,
  titleId,
  level = 2,
  rows,
  announcement = null,
  statusLine = null,
  controls = null,
  className,
}: {
  title: string;
  titleId: string;
  /** The heading level where it stands: `2` on the play screen, `4` in Hjem's game card. */
  level?: 2 | 4;
  rows: SeatStatusRow[];
  announcement?: string | null;
  statusLine?: ReactNode;
  controls?: ReactNode;
  className?: string;
}) {
  const Heading = level === 2 ? "h2" : "h4";
  return (
    <section aria-labelledby={titleId} className={className} data-seat-status="">
      <Heading
        id={titleId}
        className={level === 2 ? "text-headline text-ink" : "text-label font-semibold text-ink"}
      >
        {title}
      </Heading>
      {statusLine}
      <ul className="mt-2 flex flex-col border-t border-hairline">
        {rows.map((row) => (
          <li key={row.key} data-state={row.state ?? undefined} className="border-b border-hairline py-2">
            <div className="flex flex-wrap items-baseline gap-x-3 text-body-phone lg:text-body">
              {row.state ? <Dot filled={row.state === "ordered"} /> : null}
              <span className="min-w-[6rem] font-semibold text-ink">{row.role}</span>
              <span className={cn("min-w-0 break-words", row.named ? "text-ink" : "text-ink-secondary")}>
                {row.holder}
              </span>
              {row.status ? <span className="ml-auto text-right text-ink-secondary">{row.status}</span> : null}
            </div>
            {row.detail}
            {row.action}
          </li>
        ))}
      </ul>
      {controls}
      <p aria-live="polite" className="sr-only" data-seat-status-announce="">
        {announcement ?? ""}
      </p>
    </section>
  );
}

function Dot({ filled }: { filled: boolean }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 12 12" className="size-3 shrink-0 self-center">
      <circle cx="6" cy="6" r="5" strokeWidth="1.5" className={filled ? "fill-ink stroke-ink" : "fill-paper stroke-ink"} />
    </svg>
  );
}
