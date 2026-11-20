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
const SQUARE = 8;

type Anchor = "start" | "middle" | "end";
type Tick = { name: DateName; ms: number; x: number; anchor: Anchor; tier: number };
type LabMark = { id: string; x: number; anchor: Anchor; tier: number; day: string; time: string };

/** The extent of a label at `x` with its anchor. */
function extent(x: number, width: number, anchor: Anchor): [number, number] {
  if (anchor === "start") return [x, x + width];
  if (anchor === "end") return [x - width, x];
  return [x - width / 2, x + width / 2];
}

/** The x of an instant on a line spanning `first` to `first + span`. */
function scale(first: number, span: number) {
  const inner = WIDTH - 2 * PAD;
  return (ms: number) => (span === 0 ? WIDTH / 2 : PAD + ((ms - first) / span) * inner);
}

/** The lowest tier whose last label ends clear of `left`; records `right` there. */
function tierFor(ends: number[], left: number, right: number): number {
  let tier = 0;
  while (ends[tier] !== undefined && ends[tier] > left - 8) tier += 1;
  ends[tier] = right;
  return tier;
}

/** Places the ticks along the line, and lifts a label to the next tier when it would overlap the
 * one before it. */
function place(dates: { name: DateName; iso: string }[], x: (ms: number) => number): Tick[] {
  const ends: number[] = [];
  return dates.map((d): Tick => {
    const ms = Date.parse(d.iso);
    const { day, time } = osloDayAndTime(d.iso);
    const width = Math.max(copy.names[d.name].length, `${day} ${time}`.length) * CHAR;
    const anchor = anchorAt(x(ms), width);
    const [left, right] = extent(x(ms), width, anchor);
    return { name: d.name, ms, x: x(ms), anchor, tier: tierFor(ends, left, right) };
  });
}

/** Centred on its mark, unless that would run off the line: then it starts or ends there. */
function anchorAt(at: number, width: number): Anchor {
  if (at - width / 2 < 0) return "start";
  return at + width / 2 > WIDTH ? "end" : "middle";
}

/** Places a Lab hour's square at its start, its day and time under it, centred unless that would
 * leave the line; a label that would overlap the one before it drops a tier. */
function placeLabs(labs: readonly { id: string; starts_at: string }[], x: (ms: number) => number): LabMark[] {
  const ends: number[] = [];
  return [...labs]
    .sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at))
    .map((lab) => {
      const at = x(Date.parse(lab.starts_at));
      const { day, time } = osloDayAndTime(lab.starts_at);
      const width = Math.max(day.length, time.length) * CHAR;
      const anchor = anchorAt(at, width);
      const [left, right] = extent(at, width, anchor);
      return { id: lab.id, x: at, anchor, tier: tierFor(ends, left, right), day, time };
    });
}

/** The baseline of a tier's first label line; tier 0 sits just over the axis. */
function labelTop(axis: number, tier: number): number {
  return axis - AXIS_GAP - 2 * LINE + 6 - tier * TIER;
}

/** The baseline of a Lab hour label's first line; tier 0 sits just under its square. */
function labTop(axis: number, tier: number): number {
  return axis + 6 + SQUARE + LINE + tier * TIER;
}

/**
 * The Datolinje (Stories 5.2 and 5.6, UX-DR51): the saved dates on one read-only line, one labelled
 * tick per date in Europe/Oslo, and each Lab hour as a `lager` square under the line at its start
 * with its day and time. A diagram of this slice in hand-made SVG, not a data chart (AD-18). Its
 * text alternative is the labelled date fields and the list of Labtimer under it; the drawing is
 * named by the same dates in one line, so its scroll region is never an empty stop for a screen
 * reader. With no saved date and no Lab hour it says so in text.
 */
export function DateLine({
  dates,
  labHours = [],
  titleId,
}: {
  dates: Partial<Record<DateName, string | null>>;
  labHours?: readonly { id: string; starts_at: string }[];
  titleId: string;
}) {
  const set = DATE_NAMES.flatMap((name) => {
    const iso = dates[name];
    return iso ? [{ name, iso }] : [];
  });
  if (set.length === 0 && labHours.length === 0) {
    return <p className="mt-3 text-body-phone text-ink-secondary lg:text-body">{copy.none}</p>;
  }
  const all = [...set.map((d) => Date.parse(d.iso)), ...labHours.map((lab) => Date.parse(lab.starts_at))];
  const first = Math.min(...all);
  const x = scale(first, Math.max(...all) - first);
  const ticks = place(set, x);
  const labs = placeLabs(labHours, x);
  const tiers = ticks.length > 0 ? Math.max(...ticks.map((t) => t.tier)) + 1 : 0;
  const labTiers = labs.length > 0 ? Math.max(...labs.map((l) => l.tier)) + 1 : 0;
  const axis = tiers * TIER + AXIS_GAP + 4;
  const height = labTiers > 0 ? labTop(axis, labTiers - 1) + LINE + 8 : axis + 12;
  const label = [
    ...set.map(({ name, iso }) => {
      const { day, time } = osloDayAndTime(iso);
      return `${copy.names[name]} ${day} ${time}`;
    }),
    ...labs.map((lab) => `${nb.sessions.labHours.markLabel} ${lab.day} ${lab.time}`),
  ].join(", ");
  const halo = { stroke: "var(--color-paper)", strokeWidth: 4, paintOrder: "stroke" } as const;
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
        {labs.map((lab) => (
          <rect
            key={`lab-${lab.id}`}
            data-lab-hour={lab.id}
            x={lab.x - SQUARE / 2}
            y={axis + 6}
            width={SQUARE}
            height={SQUARE}
            fill="var(--color-lager)"
          />
        ))}
        {ticks.map((tick) => {
          const { day, time } = osloDayAndTime(set.find((d) => d.name === tick.name)!.iso);
          const tx = tick.anchor === "start" ? tick.x + 4 : tick.anchor === "end" ? tick.x - 4 : tick.x;
          const top = labelTop(axis, tick.tier);
          return (
            <g key={`label-${tick.name}`}>
              <text x={tx} y={top} textAnchor={tick.anchor} fontSize={FONT} fontWeight="600" fill="var(--color-ink)" {...halo}>
                {copy.names[tick.name]}
              </text>
              <text x={tx} y={top + LINE} textAnchor={tick.anchor} fontSize={FONT} fill="var(--color-ink-secondary)" {...halo}>
                {`${day} ${time}`}
              </text>
            </g>
          );
        })}
        {labs.map((lab) => {
          const top = labTop(axis, lab.tier);
          return (
            <g key={`lab-label-${lab.id}`}>
              <text x={lab.x} y={top} textAnchor={lab.anchor} fontSize={FONT} fill="var(--color-ink)" {...halo}>
                {lab.day}
              </text>
              <text x={lab.x} y={top + LINE} textAnchor={lab.anchor} fontSize={FONT} fill="var(--color-ink-secondary)" {...halo}>
                {lab.time}
              </text>
            </g>
          );
        })}
      </svg>
    </ScrollRegion>
  );
}
