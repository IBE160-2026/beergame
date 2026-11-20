"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type KeyboardEvent, type RefObject, useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { ScrollRegion } from "@/components/scroll-region";
import { ViewToggle } from "@/components/view-toggle";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";

import { gameLine, nextGame, ticks } from "./allocation";
import {
  type Allocation,
  type AllocationGame,
  allocationKey,
  type ClassSession,
  openAllocation,
  redrawAllocation,
  useAllocation,
} from "./api";
import { roleName } from "./sessions";

const copy = nb.sessions.allocation;

/**
 * «Fordeling» on the Klasseøkt (Story 5.8, FR-20, UX-DR50): closed, the state line and a Lenke that
 * opens the Fordelingsforhåndsvisning in place, with focus moved to its heading. Opening draws the
 * draft when none is stored (a Lecturer before the Start date); the panel always shows the stored
 * draft. «Kjør fordeling på nytt» replaces it; nobody is told. An Assistant lecturer, or anyone once
 * the session is locked, reads the stored draft only.
 */
export function AllocationBlock({ item }: { item: ClassSession }) {
  const queryClient = useQueryClient();
  const ids = useId();
  const found = useAllocation(item.id);
  const [open, setOpen] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const openerRef = useRef<HTMLButtonElement>(null);
  const canDraw = item.can_manage && !item.locked;
  const allocation = found.data;
  const opening = useAction({
    mutationFn: () => openAllocation(item.id),
    messages: { session_locked: copy.locked },
    fallback: copy.failed,
    onSuccess: (result) => {
      queryClient.setQueryData(allocationKey(item.id), result);
      setOpen(true);
    },
  });
  useEffect(() => {
    if (open) headingRef.current?.focus();
  }, [open]);

  const draft = allocation?.draft ?? null;
  const nobody = allocation !== undefined && allocation.registered_count === 0;
  // A draft stored before every Student left can still be seen, and cleared by a new draw.
  const openable = allocation !== undefined && (draft !== null || (!nobody && canDraw));
  // A redraw with nobody left removes the draft: the panel closes to the block.
  useEffect(() => {
    if (open && allocation !== undefined && draft === null) {
      setOpen(false);
      requestAnimationFrame(() => openerRef.current?.focus());
    }
  }, [open, allocation, draft]);

  if (open && allocation?.draft) {
    return (
      <section aria-labelledby={`${ids}-heading`} className="mt-10 min-w-0">
        <Preview
          item={item}
          allocation={allocation}
          headingId={`${ids}-heading`}
          headingRef={headingRef}
          canDraw={canDraw}
          onClose={() => {
            setOpen(false);
            requestAnimationFrame(() => openerRef.current?.focus());
          }}
        />
      </section>
    );
  }
  return (
    <section aria-labelledby={`${ids}-title`} className="mt-10 min-w-0">
      <h2 id={`${ids}-title`} className="text-headline text-ink">
        {copy.title}
      </h2>
      {allocation === undefined ? (
        found.isError ? (
          <p className="mt-2 text-body-phone text-ink-secondary">{copy.failed}</p>
        ) : null
      ) : (
        <p className="mt-2 text-body-phone text-ink lg:text-body">
          {nobody && draft === null ? copy.nobody : copy.notConfirmed}
        </p>
      )}
      {openable ? (
        <button
          ref={openerRef}
          type="button"
          className={LINK_BUTTON}
          aria-disabled={opening.isPending || undefined}
          onClick={() => {
            if (opening.isPending) return;
            if (canDraw) opening.mutate();
            else setOpen(true);
          }}
        >
          {opening.isPending ? copy.opening : copy.open}
        </button>
      ) : null}
      <ActionError message={opening.errorMessage} />
    </section>
  );
}

type View = "chart" | "list";

function Preview({
  item,
  allocation,
  headingId,
  headingRef,
  canDraw,
  onClose,
}: {
  item: ClassSession;
  allocation: Allocation;
  headingId: string;
  headingRef: RefObject<HTMLHeadingElement | null>;
  canDraw: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const ids = useId();
  const draft = allocation.draft!;
  const games = draft.games;
  const [view, setView] = useState<View>("chart");
  const [selected, setSelected] = useState(1);
  const [result, setResult] = useState("");
  const shown = games.find((game) => game.number === selected) ?? games[0];
  const students = games.reduce((sum, game) => sum + game.seats.filter((seat) => seat.user_id != null).length, 0);
  const redraw = useAction({
    mutationFn: () => redrawAllocation(item.id),
    messages: { session_locked: copy.locked },
    fallback: copy.failed,
    onSuccess: (next) => {
      queryClient.setQueryData(allocationKey(item.id), next);
      setSelected(1);
      setResult(copy.redrawn);
    },
  });
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 id={headingId} ref={headingRef} tabIndex={-1} className="text-headline text-ink focus:outline-none">
          {copy.heading(games.length)}
        </h2>
        <p className="mt-2 max-w-prose text-body-phone text-ink-secondary">{copy.lead(students)}</p>
        <p className="max-w-prose text-body-phone text-ink-secondary">{copy.emptySeats}</p>
        {allocation.missing_count > 0 ? (
          <p className="mt-2 max-w-prose text-body-phone text-ink">
            {copy.missing(allocation.missing_count)}
            {canDraw ? ` ${copy.missingRedraw}` : null}
          </p>
        ) : null}
      </div>
      <ViewToggle<View>
        name={`${ids}-view`}
        legend={copy.view}
        options={[
          { value: "chart", label: copy.chart },
          { value: "list", label: copy.list },
        ]}
        value={view}
        onChange={setView}
        className="lg:[&_label]:flex-none"
      />
      {view === "chart" ? (
        <>
          <p id={`${ids}-chart`} className="sr-only">
            {copy.chartLabel}
          </p>
          <ScrollRegion labelledBy={`${ids}-chart`}>
            <AllocationChart games={games} selected={shown.number} onSelect={setSelected} />
          </ScrollRegion>
          <p className="text-body-phone text-ink lg:text-body">
            <span className="mr-3 font-semibold">{copy.game(shown.number)}</span>
            {gameLine(shown)}
          </p>
        </>
      ) : (
        <ol aria-label={copy.heading(games.length)} className="flex flex-col gap-1">
          {games.map((game) => (
            <li key={game.number} className="text-body-phone text-ink lg:text-body">
              <span className="mr-3 font-semibold">{copy.game(game.number)}</span>
              {gameLine(game)}
            </li>
          ))}
        </ol>
      )}
      <div className="flex flex-col items-start gap-3 lg:flex-row lg:items-center lg:gap-6">
        {canDraw ? (
          <Button
            variant="secondary"
            unavailable={redraw.isPending}
            onClick={() => {
              if (redraw.isPending) return;
              // Cleared first, so a second redraw is announced again.
              setResult("");
              redraw.mutate();
            }}
          >
            {redraw.isPending ? copy.redrawing : copy.redraw}
          </Button>
        ) : null}
        {canDraw ? <p className="text-body-phone text-ink-secondary">{copy.noticeLine}</p> : null}
        <button type="button" className={LINK_BUTTON} onClick={onClose}>
          {copy.close}
        </button>
      </div>
      <ActionError message={redraw.errorMessage} />
      <p role="status" className="text-body-phone text-ink">
        {result}
      </p>
    </div>
  );
}

// Drawn at its natural width, one SVG unit to one CSS pixel, so the 13 px labels keep DESIGN.md's
// floor; a wide allocation scrolls in its own region (UX-DR75).
const LABEL = 92;
const FONT = 13;
const ROW = 30;
const ROW_GAP = 6;
const TOP = 6;
const TICKS = 22;
const ROOM = 460;

/** The column pitch: wide while there are few games, down to 10 px as in mockup 03. */
function pitchFor(count: number): number {
  return Math.max(10, Math.min(48, Math.floor(ROOM / Math.max(1, count))));
}

/**
 * The Fordelingsforhåndsvisning (UX-DR50, UX-DR73): one column per Class game by four Role rows,
 * Fabrikk at the top, a filled `bar-base` cell for a Student and an outlined one for an empty Seat
 * (KI-spiller). The selected column is framed in `ink`. A diagram of this slice in plain SVG, not
 * an AD-18 chart. The columns are one tab stop: ←/→, Home and End move the selection, a click
 * selects. The selected game's line under it and «Vis som liste» say the same in text.
 */
function AllocationChart({
  games,
  selected,
  onSelect,
}: {
  games: AllocationGame[];
  selected: number;
  onSelect: (number: number) => void;
}) {
  const refs = useRef(new Map<number, SVGGElement>());
  const [focused, setFocused] = useState(false);
  const pitch = pitchFor(games.length);
  const cell = Math.max(7, Math.round(pitch * 0.78));
  const roles = games[0]?.seats.map((seat) => seat.role) ?? [];
  const height = TOP + roles.length * (ROW + ROW_GAP) + TICKS;
  const width = LABEL + games.length * pitch + 16;
  const x = (index: number) => LABEL + index * pitch + (pitch - cell) / 2;
  const y = (row: number) => TOP + row * (ROW + ROW_GAP);
  const move = (event: KeyboardEvent<SVGGElement>) => {
    const next = nextGame(event.key, selected, games.length);
    if (next !== null) {
      event.preventDefault();
      onSelect(next);
      refs.current.get(next)?.focus();
    } else if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
    }
  };
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="block" focusable="false">
      {roles.map((role, row) => (
        <text
          key={role}
          x={0}
          y={y(row) + ROW / 2 + FONT / 2 - 2}
          fontSize={FONT}
          fill="var(--color-ink)"
          aria-hidden="true"
        >
          {roleName(role)}
        </text>
      ))}
      {games.map((game, index) => {
        const isSelected = game.number === selected;
        return (
          <g
            key={game.number}
            ref={(node) => {
              if (node) refs.current.set(game.number, node);
              else refs.current.delete(game.number);
            }}
            role="button"
            tabIndex={isSelected ? 0 : -1}
            aria-pressed={isSelected}
            aria-label={`${copy.game(game.number)}: ${gameLine(game)}`}
            className="cursor-pointer outline-none"
            onClick={() => onSelect(game.number)}
            onKeyDown={move}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
          >
            {/* The whole column takes the click, gaps included. */}
            <rect x={LABEL + index * pitch} y={0} width={pitch} height={y(roles.length)} fill="transparent" />
            {game.seats.map((seat, row) =>
              seat.user_id != null ? (
                <rect key={seat.role} x={x(index)} y={y(row)} width={cell} height={ROW} fill="var(--color-bar-base)" />
              ) : (
                <rect
                  key={seat.role}
                  x={x(index) + 0.5}
                  y={y(row) + 0.5}
                  width={cell - 1}
                  height={ROW - 1}
                  fill="var(--color-paper)"
                  stroke="var(--color-ink-muted)"
                  strokeWidth={1}
                />
              ),
            )}
            {isSelected ? (
              <rect
                x={x(index) - 2}
                y={y(0) - 3}
                width={cell + 4}
                height={y(roles.length) - ROW_GAP - y(0) + 6}
                fill="none"
                stroke="var(--color-ink)"
                strokeWidth={focused ? 3 : 1.5}
              />
            ) : null}
          </g>
        );
      })}
      {ticks(games.length, selected, Math.ceil(28 / pitch)).map((number) => (
        <text
          key={number}
          x={LABEL + (number - 1) * pitch + pitch / 2}
          y={height - 4}
          fontSize={FONT}
          textAnchor="middle"
          fontWeight={number === selected ? 600 : 400}
          fill={number === selected ? "var(--color-ink)" : "var(--color-ink-muted)"}
          aria-hidden="true"
        >
          {number}
        </text>
      ))}
    </svg>
  );
}
