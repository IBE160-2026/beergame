import { type ReactNode, useId } from "react";

import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";

import type { GameSettings } from "./api";
import { chainText, customerLines, roleName, upstreamFirst } from "./sessions";

const copy = nb.sessions.chain;

// The diagram is drawn at its natural width or wider, so one SVG unit is at least one CSS pixel and
// the 13-unit labels keep DESIGN.md's 13 px floor (Typography → Floors), on a phone too.
const ROLE_W = 52;
const SLOT_W = 20;
const SLOT_H = 12;
const PIPE_PAD = 14;
const PIPE_Y = 44;
const DOT_Y = 110;
const END_W = 104;
/** About the widest a 13 px glyph of these labels runs, to keep the demand lines inside. */
const CHAR_W = 7.5;
const HEIGHT = 120;
/** Room for «Maks N» under a capped Role (Story 5.15). */
const CAPPED_HEIGHT = 130;
const FONT = 13;

/** One pipe segment: `slots` boxes on a line ending in an arrow. */
function Pipe({ x, slots, label }: { x: number; slots: number; label: string }) {
  const width = pipeWidth(slots);
  return (
    <g>
      <text x={x + width / 2} y={PIPE_Y - 12} textAnchor="middle" fontSize={FONT} fill="var(--color-ink-secondary)">
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
 * the pipe (one per Week of delay, each holding the supply-line units), Lager per Role, the
 * Orders on their way as dots under the pipes, and the Demand pattern under «Kundene» (mockup 03,
 * Issue #98). A diagram of this slice in hand-made SVG, not a
 * data chart (AD-18). Every value comes from the API; the same values stand as text under it,
 * and that text labels the figure for screen readers.
 */
export function ChainDiagram({
  settings,
  capacityEnabled = false,
}: {
  settings: GameSettings;
  /** `FEATURE_CAPACITY` (Story 5.15): a capped Role is marked «Maks N» and named in the text. */
  capacityEnabled?: boolean;
}) {
  const capacityOf = (role: string): number | undefined =>
    capacityEnabled ? settings.capacity?.[role as keyof NonNullable<GameSettings["capacity"]>] : undefined;
  const textId = useId();
  const titleId = useId();
  const roles = upstreamFirst(settings);
  const parts: ReactNode[] = [];
  const [demandLine, demandFrom] = customerLines(settings.demand);
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
        <text x={x + ROLE_W / 2} y={PIPE_Y + 34} textAnchor="middle" fontSize={FONT} fontWeight="600" fill="var(--color-ink)">
          {roleName(role)}
        </text>
        <text x={x + ROLE_W / 2} y={PIPE_Y + 51} textAnchor="middle" fontSize={FONT} fill="var(--color-ink-secondary)">
          {copy.inventory(settings.starting_inventory)}
        </text>
        {capacityOf(role) === undefined ? null : (
          <text x={x + ROLE_W / 2} y={PIPE_Y + 69} textAnchor="middle" fontSize={FONT} fontWeight="600" fill="var(--color-ink)">
            {copy.capped(capacityOf(role) ?? 0)}
          </text>
        )}
      </g>,
    );
    x += ROLE_W;
  });
  parts.push(
    <g key="customers">
      <line x1={x + 4} y1={PIPE_Y} x2={x + 22} y2={PIPE_Y} stroke="var(--color-lager)" strokeWidth="1.5" />
      <path d={`M ${x + 18} ${PIPE_Y - 4} L ${x + 23} ${PIPE_Y} L ${x + 18} ${PIPE_Y + 4}`} fill="none" stroke="var(--color-lager)" strokeWidth="1.5" />
      <text x={x + 26} y={PIPE_Y + 5} fontSize={FONT} fontWeight="600" fill="var(--color-ink)">
        {copy.customers}
      </text>
      <text x={x + 26} y={PIPE_Y + 22} fontSize={FONT} fontWeight="600" fill="var(--color-lager)">
        {demandLine}
      </text>
      <text x={x + 26} y={PIPE_Y + 38} fontSize={FONT} fill="var(--color-lager)">
        {demandFrom}
      </text>
    </g>,
  );
  // Wide enough for the longest demand line under «Kundene» («100, så 100 ± 20»).
  const longest = Math.max(copy.customers.length, demandLine.length, demandFrom.length);
  const width = x + Math.max(END_W, 26 + Math.ceil(longest * CHAR_W) + 8);
  const height = roles.some((role) => capacityOf(role) !== undefined) ? CAPPED_HEIGHT : HEIGHT;
  return (
    <figure className="m-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 id={titleId} className="text-label text-ink">
          {copy.title}
        </h3>
        <p className="text-body-phone text-ink-secondary">{copy.caption}</p>
      </div>
      {/* Below its natural width the diagram scrolls inside its own region, with a fading edge on
          the side that has more, so its labels stay readable on a phone (as the Datolinje,
          UX-DR75, Issue #98); the page itself never scrolls sideways. */}
      <ScrollRegion labelledBy={titleId} className="mt-3 max-w-2xl">
        <svg
          role="img"
          aria-labelledby={textId}
          viewBox={`0 0 ${width} ${height}`}
          style={{ minWidth: `${width}px` }}
          className="block h-auto w-full"
          preserveAspectRatio="xMinYMid meet"
        >
          {parts}
        </svg>
      </ScrollRegion>
      <figcaption id={textId} className="mt-3 max-w-2xl text-body-phone text-ink-secondary">
        {chainText(settings, capacityEnabled)}
      </figcaption>
    </figure>
  );
}
