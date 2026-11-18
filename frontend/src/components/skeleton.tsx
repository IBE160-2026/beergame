import { nb } from "@/copy/nb";

/**
 * Skjelett (DESIGN.md → Components → System, UX-DR58). The layout that is coming, while a page
 * loads: a bar where the heading will stand, then `hairline` rules with an `ink-muted` row label
 * and `axis` column ticks in the real columns. No numbers, no marks, no spinner, nothing moves.
 * It is decorative (`aria-hidden`); `LoadingNote` says «Laster …» once the wait is long enough.
 *
 * `rows` and `columns` follow the page's real table; a page with no table yet shows the heading
 * and one rule.
 */
export function Skeleton({ heading = true, rows = 1, columns = 0 }: { heading?: boolean; rows?: number; columns?: number }) {
  return (
    <div aria-hidden="true" data-skeleton="" className="max-w-3xl">
      {heading ? <div className="h-8 w-48 max-w-full rounded-sm bg-hairline lg:h-10 lg:w-64" /> : null}
      <div className="mt-6">
        {Array.from({ length: rows }, (_, row) => (
          <div key={row} className="flex min-h-control-height-phone items-center gap-4 border-b border-hairline">
            <div className="w-24 shrink-0 border-t-8 border-ink-muted" />
            {Array.from({ length: columns }, (_, column) => (
              <div key={column} className="h-3 flex-1 border-l border-axis" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/** «Laster …», shown only when `visible` (after 1 s, `LOADING_TEXT_AFTER_MS`). The polite status
 * region is always there, so the text is announced when it appears. */
export function LoadingNote({ visible }: { visible: boolean }) {
  return (
    <p role="status" className="mt-4 text-body-phone text-ink-secondary lg:text-body">
      {visible ? nb.system.loading : null}
    </p>
  );
}
