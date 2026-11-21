"use client";

import { useId, useRef, useState } from "react";

import { MatrixTable } from "@/components/charts/matrix-table";
import type { TableSort } from "@/components/charts/matrix-table-sort";
import { MatrixWall } from "@/components/charts/matrix-wall";
import type { WallPosition } from "@/components/charts/matrix-wall-layout";
import { ViewToggle } from "@/components/view-toggle";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { roleName } from "@/modules/sessions/sessions";

import { useGameWeeks } from "./api";
import { DEFAULT_WALL_ROLE, type OverviewGroup, TABLE_COLUMNS, TABLE_SORT, tableRows, wallGroups } from "./overview";
import { formatCell, wallCopy, type WallRole } from "./wall-copy";

/** Until the box is measured (a server render): a laptop column and the caption size. */
const FALLBACK = { width: 960, fontSize: 13 };

type View = "wall" | "table";

/**
 * The Oversikt's Matrisevegg (Story 7.2, FR-39, UX-DR41) and its «Vis som tabell» (Story 7.3,
 * UX-DR42): the same groups as the list, one row per Class game with `role`'s Netto lager per Uke,
 * the Role and measure named above it. The Visningsbryter above switches between the wall and the
 * table, both fed by the same rows; the game that holds the keyboard's place is shared, so it
 * stays the same game (by id) in either view, and the table's sort outlasts a switch to the wall. Each started game's weeks are fetched on demand and
 * again only when its `version` changes (AD-10, AD-25); a game that has not started has none to
 * fetch. Fabrikk until another Role is chosen (Story 7.4).
 */
export function OverviewWall({
  groups,
  now,
  role = DEFAULT_WALL_ROLE,
}: {
  groups: readonly OverviewGroup[];
  now: number;
  role?: WallRole;
}) {
  const ids = useId();
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const [view, setView] = useState<View>("wall");
  const [position, setPosition] = useState<WallPosition | null>(null);
  const [sort, setSort] = useState<TableSort>(TABLE_SORT);
  const started = groups.flatMap((group) => group.games).filter((game) => game.status !== "not_started");
  const weeks = useGameWeeks(started);
  const copy = wallCopy(role, true);
  const table = nb.wall.table;
  return (
    <div ref={box} className="mt-8 min-w-0 text-caption" data-overview-wall="">
      <ViewToggle<View>
        name={`${ids}-view`}
        legend={table.view}
        options={[
          { value: "wall", label: table.wall },
          { value: "table", label: table.table },
        ]}
        value={view}
        onChange={setView}
        className="mb-4 max-w-md"
      />
      <p className="mb-2 text-label text-ink">{nb.wall.shown(nb.terms.netInventory, roleName(role))}</p>
      {view === "wall" ? (
        <MatrixWall
          width={size.width}
          fontSize={size.fontSize}
          groups={wallGroups(groups, weeks, role, now)}
          copy={copy}
          format={formatCell}
          position={position}
          onPosition={setPosition}
        />
      ) : (
        <MatrixTable
          rows={tableRows(groups, weeks, role, now)}
          columns={TABLE_COLUMNS}
          copy={{ region: copy.region, caption: copy.title, gameHeader: copy.gameHeader, week: nb.terms.week }}
          format={formatCell}
          gameFirst="ascending"
          sort={sort}
          onSort={setSort}
          focusId={position?.id ?? null}
          onFocusId={(id) => setPosition((was) => ({ id, week: was?.week ?? 1 }))}
        />
      )}
    </div>
  );
}
