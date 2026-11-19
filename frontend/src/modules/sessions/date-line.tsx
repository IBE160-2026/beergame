import { ScrollRegion } from "@/components/scroll-region";
import { nb } from "@/copy/nb";

import { DATE_NAMES, type DateName, osloDayAndTime } from "./dates";

const copy = nb.sessions.dates;

// Drawn at its natural width or wider, so one SVG unit is at least one CSS pixel and the 13-unit
// labels keep DESIGN.md's 13 px floor; below that width the line scrolls in its own region.
const WIDTH = 520;
const PAD = 8;
const FONT = 13;
const LINE = 16;
const CHAR = 7.2;
const TIER = 2 * LINE + 8;
const AXIS_GAP = 12;

type Tick = { name: DateName; ms: number; x: number; anchor: "start" | "middle" | "end"; tier: number };

/** The extent of a label at `x` with its anchor. */
function extent(x: number, width: number, anchor: Tick["anchor"]): [number, number] {
  if (anchor === "start") return [x, x + width];
  if (anchor === "end") return [x - width, x];
  return [x - width / 2, x + width / 2];
}

/** Places the ticks along the line, and lifts a label to the next tier when it would overlap the
 * one before it. */
function place(dates: { name: DateName; iso: string }[]): { ticks: Tick[]; tiers: number } {
  const ms = dates.map((d) => Date.parse(d.iso));
  const first = Math.min(...ms);
  const span = Math.max(...ms) - first;
  const inner = WIDTH - 2 * PAD;
  const ends: number[] = [];
  const ticks = dates.map((d, i): Tick => {
    const x = span === 0 ? WIDTH / 2 : PAD + ((ms[i] - first) / span) * inner;
    const anchor = dates.length === 1 ? "middle" : i === 0 ? "start" : i === dates.length - 1 ? "end" : "middle";
    const { day, time } = osloDayAndTime(d.iso);
    const width = Math.max(copy.names[d.name].length, `${day} ${time}`.length) * CHAR;
    const [left, right] = extent(x, width, anchor);
    let tier = 0;
    while (ends[tier] !== undefined && ends[tier] > left - 8) tier += 1;
    ends[tier] = right;
    return { name: d.name, ms: ms[i], x, anchor, tier };
  });
  return { ticks, tiers: Math.max(...ticks.map((t) => t.tier)) + 1 };
}

/** The baseline of a tier's first label line; tier 0 sits just over the axis. */
function labelTop(axis: number, tier: number): number {
  return axis - AXIS_GAP - 2 * LINE + 6 - tier * TIER;
}

/**
 * The Datolinje (Story 5.2, UX-DR51): the saved dates on one read-only line, one labelled tick per
 * date in Europe/Oslo. A diagram of this slice in hand-made SVG, not a data chart (AD-18). Its text
 * alternative is the labelled date fields under it; the drawing is named by the same dates in one
 * line, so its scroll region is never an empty stop for a screen reader. With no saved date it says
 * so in text.
 */
export function DateLine({ dates, titleId }: { dates: Partial<Record<DateName, string | null>>; titleId: string }) {
  const set = DATE_NAMES.flatMap((name) => {
    const iso = dates[name];
    return iso ? [{ name, iso }] : [];
  });
  if (set.length === 0) {
    return <p className="mt-3 text-body-phone text-ink-secondary lg:text-body">{copy.none}</p>;
  }
  const { ticks, tiers } = place(set);
  const axis = tiers * TIER + AXIS_GAP + 4;
  const height = axis + 12;
  const label = set
    .map(({ name, iso }) => {
      const { day, time } = osloDayAndTime(iso);
      return `${copy.names[name]} ${day} ${time}`;
    })
    .join(", ");
  return (
    <ScrollRegion labelledBy={titleId} className="mt-3">
      <svg
        role="img"
        aria-label={label}
        focusable="false"
        data-testid="date-line"
        viewBox={`0 0 ${WIDTH} ${height}`}
        style={{ minWidth: `${WIDTH}px` }}
        className="block h-auto w-full"
        preserveAspectRatio="xMinYMid meet"
      >
        <line x1={PAD} y1={axis} x2={WIDTH - PAD} y2={axis} stroke="var(--color-axis)" strokeWidth="1" />
        {/* The ticks first, then the labels over them with a `paper` halo, so a tick lifted to a
            higher tier never runs through a label below it. */}
        {ticks.map((tick) => (
          <line
            key={`tick-${tick.name}`}
            data-tick={tick.name}
            x1={tick.x}
            y1={labelTop(axis, tick.tier) + 2 * LINE - 6}
            x2={tick.x}
            y2={axis + 8}
            stroke="var(--color-ink)"
            strokeWidth="1.5"
          />
        ))}
        {ticks.map((tick) => {
          const { day, time } = osloDayAndTime(set.find((d) => d.name === tick.name)!.iso);
          const x = tick.anchor === "start" ? tick.x + 4 : tick.anchor === "end" ? tick.x - 4 : tick.x;
          const top = labelTop(axis, tick.tier);
          const halo = { stroke: "var(--color-paper)", strokeWidth: 4, paintOrder: "stroke" } as const;
          return (
            <g key={`label-${tick.name}`}>
              <text x={x} y={top} textAnchor={tick.anchor} fontSize={FONT} fontWeight="600" fill="var(--color-ink)" {...halo}>
                {copy.names[tick.name]}
              </text>
              <text x={x} y={top + LINE} textAnchor={tick.anchor} fontSize={FONT} fill="var(--color-ink-secondary)" {...halo}>
                {`${day} ${time}`}
              </text>
            </g>
          );
        })}
      </svg>
    </ScrollRegion>
  );
}
