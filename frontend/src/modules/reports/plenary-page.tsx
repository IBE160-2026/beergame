"use client";

import { useId, useRef, useState } from "react";

import { MatrixTable } from "@/components/charts/matrix-table";
import { MatrixWall } from "@/components/charts/matrix-wall";
import type { WallPosition } from "@/components/charts/matrix-wall-layout";
import { ViewToggle } from "@/components/view-toggle";
import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { useBoxSize } from "@/lib/box-size";
import { usePageState } from "@/lib/page-state";
import { PROJECTOR_SCALE } from "@/lib/projector";
import type { WallFilter } from "@/modules/games/api";
import { formatCell, measureName, wallCopy } from "@/modules/games/wall-copy";
import { RoleFilter } from "@/modules/games/wall-filters";
import type { SessionUser } from "@/modules/identity/api";
import { AccessDenied, GuardedPage } from "@/modules/identity/home-page";
import { classOverviewPath } from "@/modules/identity/homes";
import { PageLink, PageShell } from "@/modules/identity/page-shell";
import { roleName } from "@/modules/sessions/sessions";

import { OrdersByRole } from "./all-games-page";
import { SECONDARY, TEXT } from "./class-report-parts";
import { type Plenary, plenaryKey, useClassPlenary } from "./plenary-api";
import { hasWeeks, plenaryGroups, plenaryOrders, plenaryTableRows, type PlenaryView } from "./plenary";

const copy = nb.plenary;

/** The shape of an id (a UUID). */
const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Until the box is measured (a server render): a laptop column and the caption size. */
const FALLBACK = { width: 960, fontSize: 13 };

/** Larger cells than the Oversikt's wall, so numbers fit more often and read from the back of the
 * room (DESIGN.md → Matrisevegg → «Vis i plenum»); the projector text scale comes on top. */
const PLENUM_FONT = 1.5;

/**
 * «Alle spill i plenum» (Story 14.6, FR-86, UX-DR42, UX-DR72): every Class game of the Class
 * session for the projector, opened from the Oversikt's «Vis i plenum». Display mode like «Delt
 * skjerm» (no header with a name, the projector text scale). The Matrisevegg of Netto lager for the
 * Role the Rolle filter chooses, with larger cells and only the game column, its legend always
 * visible and the caption in words under it; the Visningsbryter offers «Vis som tabell» (game-number
 * order, nothing to sort) and 14.5's Orders charts per Role (no game marked). The page reads only
 * `getClassPlenary`, which holds game numbers and per-Week values: never the staff overview, so no
 * name, wait, status, Varselbånd or Spillstyring can reach the screen (AD-14). `session:<id>`
 * reads it again; focus stays on the same game across reads.
 */
export function PlenaryPage({ sessionId }: { sessionId: string }) {
  return (
    <GuardedPage page="lecturerHome">
      {(user, updatedAt) =>
        ID.test(sessionId) ? (
          <PlenaryView sessionId={sessionId.toLowerCase()} user={user} updatedAt={updatedAt} />
        ) : (
          <AccessDenied user={user} updatedAt={updatedAt} />
        )
      }
    </GuardedPage>
  );
}

function PlenaryView({ sessionId, user, updatedAt }: { sessionId: string; user: SessionUser; updatedAt: number }) {
  const found = useClassPlenary(sessionId);
  const { phase, retry } = usePageState(found, plenaryKey(sessionId));
  if (found.error instanceof ApiRequestError && found.error.code === "forbidden") {
    return <AccessDenied user={user} updatedAt={updatedAt} />;
  }
  const data = found.data;
  // No `user`: display mode shows no header with a name on the projector.
  return (
    <PageShell
      wide
      title={copy.title}
      updatedAt={found.dataUpdatedAt || updatedAt}
      phase={data ? "ready" : phase === "ready" ? "loading" : phase}
      onRetry={retry}
    >
      <div className="min-w-0" data-plenary={data && hasWeeks(data) ? "open" : "none"}>
        <style>{PROJECTOR_SCALE}</style>
        <p className={`mt-1 ${TEXT}`} data-plenary-line="">
          {copy.line}
        </p>
        <PageLink href={classOverviewPath(sessionId)}>{copy.back}</PageLink>
        {data && hasWeeks(data) ? (
          <Views data={data} />
        ) : data ? (
          <p className={`mt-6 max-w-2xl ${TEXT}`}>{copy.none}</p>
        ) : null}
      </div>
    </PageShell>
  );
}

function Views({ data }: { data: Plenary }) {
  const ids = useId();
  const [view, setView] = useState<PlenaryView>("wall");
  const [role, setRole] = useState<WallFilter["role"]>("factory");
  // The game that holds the keyboard's place, shared by the wall and the table, by game number.
  const [position, setPosition] = useState<WallPosition | null>(null);
  const table = nb.wall.table;
  return (
    <div className="mt-6 min-w-0">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        {view === "orders" ? <p className={SECONDARY}>{nb.allGames.axis}</p> : <RoleFilter role={role} onChange={setRole} />}
        <ViewToggle<PlenaryView>
          name={`${ids}-view`}
          legend={table.view}
          options={[
            { value: "wall", label: table.wall },
            { value: "table", label: table.table },
            { value: "orders", label: copy.orders },
          ]}
          value={view}
          onChange={setView}
        />
      </div>
      {view === "orders" ? (
        <div className="flex min-w-0 flex-col gap-8" data-plenary-orders="">
          <OrdersByRole data={plenaryOrders(data)} />
        </div>
      ) : (
        <>
          <p className="mb-3 text-label text-ink">{nb.wall.shown(measureName("net"), roleName(role))}</p>
          {view === "wall" ? (
            <Wall data={data} role={role} position={position} onPosition={setPosition} />
          ) : (
            <MatrixTable
              rows={plenaryTableRows(data, role)}
              columns={[]}
              copy={{
                region: nb.wall.region,
                caption: wallCopy(role, false).title,
                gameHeader: nb.wall.gameHeader,
                week: nb.terms.week,
              }}
              format={formatCell}
              focusId={position?.id ?? null}
              onFocusId={(id) => setPosition((was) => ({ id, week: was?.week ?? 1 }))}
            />
          )}
        </>
      )}
    </div>
  );
}

function Wall({
  data,
  role,
  position,
  onPosition,
}: {
  data: Plenary;
  role: WallFilter["role"];
  position: WallPosition | null;
  onPosition: (position: WallPosition) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  return (
    <div ref={box} className="min-w-0 text-caption" data-plenary-wall="">
      <MatrixWall
        width={size.width}
        fontSize={Math.round(size.fontSize * PLENUM_FONT)}
        groups={plenaryGroups(data, role)}
        copy={wallCopy(role, false)}
        format={formatCell}
        scale="net"
        position={position}
        onPosition={onPosition}
      />
      <p className="mt-3 max-w-3xl text-body-phone text-ink lg:text-body" data-plenary-caption="">
        {copy.caption}
      </p>
    </div>
  );
}
