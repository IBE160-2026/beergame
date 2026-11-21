"use client";

import { useId, useRef, useState } from "react";

import { MatrixTable } from "@/components/charts/matrix-table";
import type { TableSort } from "@/components/charts/matrix-table-sort";
import { MatrixWall } from "@/components/charts/matrix-wall";
import type { WallPosition } from "@/components/charts/matrix-wall-layout";
import { colour } from "@/components/charts/palette";
import { ViewToggle } from "@/components/view-toggle";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { roleName } from "@/modules/sessions/sessions";

import { useGameWeeks, useWallAggregates, type WallFilter } from "./api";
import {
  DEFAULT_WALL_FILTER,
  filterGroups,
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
 */
export function OverviewWall({
  sessionId,
  groups,
  now,
}: {
  sessionId: string;
  groups: readonly OverviewGroup[];
  now: number;
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
  const shown = filterGroups(groups, filter.status);
  const { role, cells } = filter;
  const copy = wallCopy(role, true, cells);
  const format = cells === "cost" ? formatCost : formatCell;
  // While another combination loads the last one stays, unless it measures something else: a
  // median of Netto lager is never drawn under Ordre cells. Its rows name their own Role.
  const shownAggregates = aggregates.data?.cells === cells ? aggregates.data : undefined;
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
