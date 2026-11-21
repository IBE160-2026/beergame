"use client";

import { type FocusEvent, useId, useRef, useState } from "react";

import { MatrixTable } from "@/components/charts/matrix-table";
import type { TableSort } from "@/components/charts/matrix-table-sort";
import { MatrixWall } from "@/components/charts/matrix-wall";
import type { WallPosition } from "@/components/charts/matrix-wall-layout";
import { colour } from "@/components/charts/palette";
import { ViewToggle } from "@/components/view-toggle";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { roleName } from "@/modules/sessions/sessions";

import { useGameWeeks, useWallAggregates, type WallAggregates, type WallFilter } from "./api";
import {
  DEFAULT_WALL_FILTER,
  filterGroups,
  type HeldOrder,
  holdGroups,
  orderOf,
  type OverviewGroup,
  statusCounts,
  TABLE_COLUMNS,
  TABLE_SORT,
  tableFooter,
  tableRows,
  wallGroups,
  wallSummary,
} from "./overview";
import { WallFilters } from "./wall-filters";
import { formatCell, formatCost, measureName, scaleOf, wallCopy } from "./wall-copy";

/** Until the box is measured (a server render): a laptop column and the caption size. */
const FALLBACK = { width: 960, fontSize: 13 };

type View = "wall" | "table";

/**
 * The Oversikt's Matrisevegg (Story 7.2, FR-39, UX-DR41), its «Vis som tabell» (Story 7.3,
 * UX-DR42) and its Veggfiltre with the class median (Story 7.4, UX-DR40, UX-DR43). The filters
 * choose the Role, what the cells show and which games; they filter the rows already received, so
 * no game's weeks are fetched again for them. The class median graph and the rows under the wall
 * come from the api for the chosen combination (AD-10). The compact Visningsbryter at the right of
 * the heading line switches between the wall and the table, both fed by the same rows; the game
 * that holds the keyboard's place is shared, and the table's sort outlasts a switch. Each started
 * game's weeks are fetched on demand and again only when its `version` changes (AD-25).
 *
 * Live (Story 7.5, UX-DR44): while keyboard focus is inside the wall its rows keep their groups
 * and places and only their values change; they re-group once focus leaves (the table holds its
 * order itself). While «Oppdater automatisk» is off (`heldAt`) the median rows stay as they were
 * for the chosen filters; a filter chosen meanwhile shows its own.
 */
export function OverviewWall({
  sessionId,
  groups,
  now,
  heldAt = null,
}: {
  sessionId: string;
  groups: readonly OverviewGroup[];
  now: number;
  /** When the held answer arrived, while «Oppdater automatisk» is off; null while it is on. */
  heldAt?: number | null;
}) {
  const ids = useId();
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const [view, setView] = useState<View>("wall");
  const [position, setPosition] = useState<WallPosition | null>(null);
  const [sort, setSort] = useState<TableSort>(TABLE_SORT);
  const [filter, setFilter] = useState<WallFilter>(DEFAULT_WALL_FILTER);
  const all = groups.flatMap((group) => group.games);
  const weeks = useGameWeeks(all.filter((game) => game.status !== "not_started"));
  const aggregates = useWallAggregates(sessionId, filter);
  const held = useHeld(
    aggregates.data,
    aggregates.isPlaceholderData,
    heldAt,
    `${filter.role}|${filter.cells}|${filter.status}`,
  );
  // The row order while keyboard focus is inside the wall.
  const [order, setOrder] = useState<HeldOrder | null>(null);
  const filtered = filterGroups(groups, filter.status);
  // A held row stays even when its new status falls outside the Status filter; a new game shows
  // only when the filter admits it.
  const admitted = new Set(filtered.flatMap((group) => group.games.map((game) => game.game_id)));
  const shown = order ? holdGroups(groups, order, (game) => admitted.has(game.game_id)) : filtered;
  const onWallFocus = () => {
    if (!order) setOrder(orderOf(filtered));
  };
  const onWallBlur = (event: FocusEvent<HTMLDivElement>) => {
    // A cell taken out of the DOM while it re-renders keeps the wall's focus (MatrixWall puts it back).
    if (!(event.target as Node).isConnected) return;
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOrder(null);
  };
  const { role, cells } = filter;
  const copy = wallCopy(role, true, cells);
  const format = cells === "cost" ? formatCost : formatCell;
  // While another combination loads the last one stays, unless it measures something else: a
  // median of Netto lager is never drawn under Ordre cells. Its rows name their own Role.
  const shownAggregates = held?.cells === cells ? held : undefined;
  const summary = shownAggregates ? wallSummary(shownAggregates, shownAggregates.role) : undefined;
  const footer = shownAggregates ? tableFooter(shownAggregates, shownAggregates.role) : undefined;
  const table = nb.wall.table;
  const median = nb.wall.median;
  return (
    <div ref={box} className="mt-8 min-w-0 text-caption" data-overview-wall="">
      <WallFilters filter={filter} counts={statusCounts(all)} onChange={setFilter} />
      <div className="mt-3 mb-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <p className="text-label text-ink">{nb.wall.shown(measureName(cells), roleName(role))}</p>
          {summary && summary.graph.some((point) => point !== null) && view === "wall" ? (
            <p className="mt-1 flex flex-wrap items-center gap-x-4 text-caption text-ink-secondary" data-median-key="">
              <span className="inline-flex items-center gap-1.5">
                <svg width="16" height="12" aria-hidden="true" className="shrink-0">
                  <line x1="0" x2="16" y1="6" y2="6" stroke={colour("ink")} strokeWidth="1.5" />
                </svg>
                {median.line}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <svg width="16" height="12" aria-hidden="true" className="shrink-0">
                  <rect width="16" height="12" fill={colour("hairline")} />
                </svg>
                {median.band}
              </span>
            </p>
          ) : null}
          {aggregates.isError && !aggregates.data ? (
            <p role="status" className="mt-1 text-caption text-ink">
              {median.failed}
            </p>
          ) : null}
        </div>
        <ViewToggle<View>
          name={`${ids}-view`}
          legend={table.view}
          options={[
            { value: "wall", label: table.wall },
            { value: "table", label: table.table },
          ]}
          value={view}
          onChange={setView}
          inline
        />
      </div>
      {shown.length === 0 ? (
        <p className="mt-4 text-body-phone text-ink lg:text-body">{nb.wall.filters.empty}</p>
      ) : view === "wall" ? (
        <div onFocus={onWallFocus} onBlur={onWallBlur}>
          <MatrixWall
            width={size.width}
            fontSize={size.fontSize}
            groups={wallGroups(shown, weeks, role, now, cells)}
            copy={copy}
            format={format}
            scale={scaleOf(cells)}
            summary={summary}
            position={position}
            onPosition={setPosition}
          />
        </div>
      ) : (
        <MatrixTable
          rows={tableRows(shown, weeks, role, now, cells)}
          columns={TABLE_COLUMNS}
          copy={{ region: copy.region, caption: copy.title, gameHeader: copy.gameHeader, week: nb.terms.week }}
          format={format}
          gameFirst="ascending"
          sort={sort}
          onSort={setSort}
          footer={footer}
          focusId={position?.id ?? null}
          onFocusId={(id) => setPosition((was) => ({ id, week: was?.week ?? 1 }))}
        />
      )}
    </div>
  );
}

/**
 * The median rows on screen: the latest while «Oppdater automatisk» is on (`heldAt` null); while
 * it is off, the rows as they stood when it was switched off or «Oppdater» was pressed, for the
 * filters then chosen. Filters chosen meanwhile show their own rows as they arrive.
 */
function useHeld(latest: WallAggregates | undefined, placeholder: boolean, heldAt: number | null, filterKey: string) {
  const [kept, setKept] = useState<{ key: string; data: WallAggregates | undefined; placeholder: boolean }>({
    key: "",
    data: undefined,
    placeholder: true,
  });
  if (heldAt === null) return latest;
  const key = `${heldAt}|${filterKey}`;
  // Taken again until it holds the combination's own answer: the last combination's rows, shown
  // while a new one loads, are never what is held for it.
  if (kept.key !== key || kept.placeholder || !kept.data) {
    // Adjusting state while rendering (React's pattern for state derived from props).
    if (kept.key !== key || kept.data !== latest || kept.placeholder !== placeholder) {
      setKept({ key, data: latest, placeholder });
    }
    return latest;
  }
  return kept.data;
}
