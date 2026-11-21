"use client";

import { useRef } from "react";

import { MatrixWall, type WallGroup } from "@/components/charts/matrix-wall";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { roleName } from "@/modules/sessions/sessions";

import { useGameWeeks } from "./api";
import { DEFAULT_WALL_ROLE, type OverviewGroup, wallGroups } from "./overview";
import { formatCell, wallCopy, type WallRole } from "./wall-copy";

/** Until the box is measured (a server render): a laptop column and the caption size. */
const FALLBACK = { width: 960, fontSize: 13 };

/**
 * The Oversikt's Matrisevegg (Story 7.2, FR-39, UX-DR41): the same groups as the list, one row per
 * Class game with `role`'s Netto lager per Uke, the Role and measure named above it. Each started
 * game's weeks are fetched on demand and again only when its `version` changes (AD-10, AD-25); a
 * game that has not started has none to fetch. Fabrikk until another Role is chosen (Story 7.4).
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
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  const started = groups.flatMap((group) => group.games).filter((game) => game.status !== "not_started");
  const weeks = useGameWeeks(started);
  const rows: WallGroup[] = wallGroups(groups, weeks, role, now);
  return (
    <div ref={box} className="mt-8 min-w-0 text-caption" data-overview-wall="">
      <p className="mb-2 text-label text-ink">{nb.wall.shown(nb.terms.netInventory, roleName(role))}</p>
      <MatrixWall width={size.width} fontSize={size.fontSize} groups={rows} copy={wallCopy(role, true)} format={formatCell} />
    </div>
  );
}
