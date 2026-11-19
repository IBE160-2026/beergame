import { type ReactNode, useId } from "react";

import { nb } from "@/copy/nb";

import type { GameSettings } from "./api";
import { chainText, roleName, upstreamFirst } from "./sessions";

const copy = nb.sessions.chain;

const ROLE_W = 44;
const SLOT_W = 16;
const SLOT_H = 10;
const PIPE_PAD = 10;
const PIPE_Y = 44;
const DOT_Y = 104;
const END_W = 84;

/** One pipe segment: `slots` boxes on a line ending in an arrow. */
function Pipe({ x, slots, label }: { x: number; slots: number; label: string }) {
  const width = pipeWidth(slots);
  return (
    <g>
      <text x={x + width / 2} y={PIPE_Y - 12} textAnchor="middle" fontSize="10" fill="var(--color-ink-secondary)">
        {label}
      </text>
      <line x1={x} y1={PIPE_Y} x2={x + width - 2} y2={PIPE_Y} stroke="var(--color-lager)" strokeWidth="1.5" />
      <path d={`M ${x + width - 6} ${PIPE_Y - 4} L ${x + width - 1} ${PIPE_Y} L ${x + width - 6} ${PIPE_Y + 4}`} fill="none" stroke="var(--color-lager)" strokeWidth="1.5" />
      {Array.from({ length: slots }, (_, i) => (
        <rect
          key={i}
          x={x + PIPE_PAD / 2 + i * SLOT_W + 1}
          y={PIPE_Y - SLOT_H / 2}
          width={SLOT_W - 4}
          height={SLOT_H}
          fill="var(--color-paper)"
          stroke="var(--color-lager)"
          strokeWidth="1.5"
        />
      ))}
    </g>
  );
}

function pipeWidth(slots: number): number {
  return Math.max(slots, 1) * SLOT_W + PIPE_PAD;
}

/** The Orders on their way upstream under a pipe: one dot per Week of order delay. */
function OrderDots({ x, width, weeks }: { x: number; width: number; weeks: number }) {
  const step = width / (weeks + 1);
  return (
    <g>
      <line x1={x + 4} y1={DOT_Y} x2={x + width - 4} y2={DOT_Y} stroke="var(--color-ink-muted)" strokeWidth="1" />
      {Array.from({ length: weeks }, (_, i) => (
        <circle key={i} cx={x + step * (i + 1)} cy={DOT_Y} r="2.5" fill="var(--color-ink)" />
      ))}
    </g>
  );
}

/**
 * «Kjeden ved start» (Story 5.1, UX-DR48): the four Roles with upstream on the left, the boxes on
 * the pipe (one per Week of delay, each holding the supply-line units), Lager per Role, and the
 * Orders on their way as dots under the pipes. A diagram of this slice in hand-made SVG, not a
 * data chart (AD-18). Every value comes from the API; the same values stand as text under it,
 * and that text labels the figure for screen readers.
 */
export function ChainDiagram({ settings }: { settings: GameSettings }) {
  const textId = useId();
  const titleId = useId();
  const roles = upstreamFirst(settings);
  const parts: ReactNode[] = [];
  let x = 0;
  roles.forEach((role, index) => {
    // Into the first (most upstream) Role: production; between Roles: shipping.
    const slots = index === 0 ? settings.production_delay : settings.shipping_delay;
    const width = pipeWidth(slots);
    parts.push(<Pipe key={`pipe-${role}`} x={x} slots={slots} label={copy.delay(slots)} />);
    if (index > 0) {
      parts.push(<OrderDots key={`dots-${role}`} x={x} width={width} weeks={settings.order_delay} />);
    }
    x += width;
    parts.push(
      <g key={`role-${role}`}>
        <rect x={x} y={PIPE_Y - 18} width={ROLE_W} height={36} fill="var(--color-lager)" />
        <text x={x + ROLE_W / 2} y={PIPE_Y + 32} textAnchor="middle" fontSize="11" fontWeight="600" fill="var(--color-ink)">
          {roleName(role)}
        </text>
        <text x={x + ROLE_W / 2} y={PIPE_Y + 46} textAnchor="middle" fontSize="10" fill="var(--color-ink-secondary)">
          {copy.inventory(settings.starting_inventory)}
        </text>
      </g>,
    );
    x += ROLE_W;
  });
  parts.push(
    <g key="customers">
      <line x1={x + 4} y1={PIPE_Y} x2={x + 22} y2={PIPE_Y} stroke="var(--color-lager)" strokeWidth="1.5" />
      <path d={`M ${x + 18} ${PIPE_Y - 4} L ${x + 23} ${PIPE_Y} L ${x + 18} ${PIPE_Y + 4}`} fill="none" stroke="var(--color-lager)" strokeWidth="1.5" />
      <text x={x + 26} y={PIPE_Y + 4} fontSize="11" fontWeight="600" fill="var(--color-ink)">
        {copy.customers}
      </text>
    </g>,
  );
  const width = x + END_W;
  return (
    <figure className="m-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 id={titleId} className="text-label text-ink">
          {copy.title}
        </h3>
        <p className="text-body-phone text-ink-secondary">{copy.caption}</p>
      </div>
      {/* Below its natural width the diagram scrolls inside its own region, so its labels stay
          readable on a phone (as the Datolinje, UX-DR75); the page itself never scrolls sideways. */}
      <div role="group" aria-labelledby={titleId} tabIndex={0} className="mt-3 max-w-2xl overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink">
        <svg
          role="img"
          aria-labelledby={textId}
          viewBox={`0 0 ${width} 116`}
          style={{ minWidth: `${width}px` }}
          className="block h-auto w-full"
          preserveAspectRatio="xMinYMid meet"
        >
          {parts}
        </svg>
      </div>
      <figcaption id={textId} className="mt-3 max-w-2xl text-body-phone text-ink-secondary">
        {chainText(settings)}
      </figcaption>
    </figure>
  );
}
