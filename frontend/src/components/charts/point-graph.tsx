"use client";

import { type KeyboardEvent, type PointerEvent, useRef } from "react";

import { CHART_FONT, colour } from "./palette";
import { scaleY } from "./scales";

/** The drawn point's diameter and the line's width (UX-DR38: an 8 px `ink` point, a 2 px line). */
const POINT = 8;
const LINE = 2;
/** A point's tap target (UX-DR76: 44 px); the caller keeps half of it free above and below. */
export const TARGET = 44;
/** How far a finger moves up or down before a touch in the graph is a drag, not a tap or a swipe. */
const DRAG_START = 6;

export type PointGraphProps = {
  width: number;
  height: number;
  /** Each Uke column's centre, from the plot's left edge (`GraphOverTable` measures them). */
  xs: readonly number[];
  /** Per Uke: its value, or null when not answered (no point). */
  values: readonly (number | null)[];
  /** Per Uke: where its slider sits while it has no value. */
  starts: readonly number[];
  /** The shown range, low to high. */
  domain: readonly [number, number];
  /** The y of the range's high and low ends, from the plot's top. */
  top: number;
  bottom: number;
  /** The SVG `<title>` (AD-18). */
  title: string;
  /** The points' group name (the graph as a view of the table). */
  label: string;
  /** Each point's name («Uke 3») and value text («Uke 3: 14 enheter»). */
  names: readonly string[];
  valueText: (index: number) => string;
  /** The labelled ticks, drawn as `hairline` grid lines. */
  ticks: readonly number[];
  /** A key on a point: the new value, or null when the key does nothing. */
  onKey: (index: number, key: string) => number | null;
  /** A pointer pressed or dragged in Uke `index`'s column at `y` (from the plot's top). */
  onPointer: (index: number, y: number) => void;
  /** A value placed by key. */
  onPlace: (index: number, value: number) => void;
};

/**
 * A drawn item's graph (Story 11.14, FR-80, UX-DR38, AD-18): over the value table's Uke columns,
 * an 8 px `ink` point per answered Uke joined to its answered neighbours by a 2 px `ink` line, and
 * no point for an Uke with no value. Hand-made SVG with a fixed size from its caller, `aria-hidden`
 * with a `<title>`: the points are read and moved as one `role="slider"` per Uke laid over it
 * (44 px targets, Up and Down by 1, Page Up and Page Down by 10), and the table under the graph is
 * the same answer. A press in a column places that Uke at the pointer's height; dragging moves it
 * while pressed. On a touch screen a tap places on lifting and a vertical drag moves the point, so
 * a sideways swipe still scrolls the region (`touch-action: pan-x`) and changes nothing.
 */
export function PointGraph({
  width,
  height,
  xs,
  values,
  starts,
  domain,
  top,
  bottom,
  title,
  label,
  names,
  valueText,
  ticks,
  onKey,
  onPointer,
  onPlace,
}: PointGraphProps) {
  const pressed = useRef<number | null>(null);
  // A touch or pen press not yet placed: a tap places it on lifting, a vertical move drags it, and
  // a sideways swipe (the region scrolls, `pointercancel`) places nothing.
  const pending = useRef<{ index: number; y: number } | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const [low, high] = domain;
  const y = scaleY(domain, top, bottom);

  const nearest = (x: number) => {
    let best = 0;
    xs.forEach((centre, i) => {
      if (Math.abs(centre - x) < Math.abs(xs[best]! - x)) best = i;
    });
    return best;
  };
  const at = (event: PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  };
  const placeAt = (index: number, pointerY: number) => {
    box.current?.querySelector<HTMLElement>(`[data-slider="${index}"]`)?.focus({ preventScroll: true });
    onPointer(index, pointerY);
  };
  const down = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 || xs.length === 0) return;
    event.preventDefault();
    const point = at(event);
    const index = nearest(point.x);
    try {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    } catch {
      // No active pointer of that id (an event made by script): the press works without capture.
    }
    if (event.pointerType === "mouse") {
      pressed.current = index;
      placeAt(index, point.y);
    } else {
      pending.current = { index, y: point.y };
    }
  };
  const move = (event: PointerEvent<HTMLDivElement>) => {
    if (event.buttons === 0) {
      // The press ended where no `pointerup` reached the graph.
      pressed.current = null;
      pending.current = null;
      return;
    }
    const pointerY = at(event).y;
    if (pending.current !== null && Math.abs(pointerY - pending.current.y) >= DRAG_START) {
      pressed.current = pending.current.index;
      pending.current = null;
    }
    if (pressed.current !== null) placeAt(pressed.current, pointerY);
  };
  const up = () => {
    if (pending.current !== null) placeAt(pending.current.index, pending.current.y);
    pressed.current = null;
    pending.current = null;
  };
  const cancel = () => {
    pressed.current = null;
    pending.current = null;
  };
  const key = (index: number) => (event: KeyboardEvent<HTMLDivElement>) => {
    // Browser and assistive-technology shortcuts keep their keys.
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const next = onKey(index, event.key);
    if (next === null) return;
    event.preventDefault();
    onPlace(index, next);
  };

  return (
    <div
      ref={box}
      role="group"
      aria-label={label}
      data-point-graph=""
      className="relative cursor-pointer touch-pan-x select-none"
      style={{ width, height }}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={cancel}
    >
      <PointMarks width={width} height={height} xs={xs} values={values} domain={domain} top={top} bottom={bottom} title={title} ticks={ticks} />
      {names.map((name, i) => {
        const value = values[i] ?? null;
        const shown = value ?? starts[i] ?? low;
        if (xs[i] === undefined) return null;
        return (
          <div
            key={i}
            role="slider"
            tabIndex={0}
            data-slider={i}
            aria-label={name}
            aria-orientation="vertical"
            aria-valuemin={low}
            aria-valuemax={high}
            aria-valuenow={shown}
            aria-valuetext={valueText(i)}
            onKeyDown={key(i)}
            className="absolute rounded-full focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ink"
            style={{
              left: xs[i]! - TARGET / 2,
              top: y(shown) - TARGET / 2,
              width: TARGET,
              height: TARGET,
            }}
          />
        );
      })}
    </div>
  );
}

export type PointMarksProps = Pick<PointGraphProps, "width" | "height" | "xs" | "values" | "domain" | "top" | "bottom" | "title" | "ticks">;

/**
 * The drawn answer itself (Story 11.14, UX-DR38): the ticks as `hairline` grid lines (`axis` at 0),
 * an 8 px `ink` point per answered Uke joined to its answered neighbours by a 2 px `ink` line, no
 * point for an Uke with no value. A fixed-size SVG, `aria-hidden` with its `<title>` (AD-18): the
 * value table is its reading. `PointGraph` lays its sliders over it; the Student report (Story
 * 13.10) draws it alone, as the image of a handed-in answer.
 */
export function PointMarks({ width, height, xs, values, domain, top, bottom, title, ticks }: PointMarksProps) {
  const y = scaleY(domain, top, bottom);
  const segments: string[] = [];
  values.forEach((value, i) => {
    const next = values[i + 1];
    if (value !== null && next !== null && next !== undefined && xs[i + 1] !== undefined) {
      segments.push(`M${xs[i]},${y(value)}L${xs[i + 1]},${y(next)}`);
    }
  });
  return (
    <svg aria-hidden="true" width={width} height={height} viewBox={`0 0 ${width} ${height}`} data-chart="points" fontFamily={CHART_FONT}>
      <title>{title}</title>
      {ticks.map((tick) => (
        <line key={tick} x1={0} x2={width} y1={y(tick)} y2={y(tick)} stroke={colour(tick === 0 ? "axis" : "hairline")} strokeWidth={1} />
      ))}
      {segments.length > 0 ? (
        <path data-mark="line" d={segments.join("")} fill="none" stroke={colour("ink")} strokeWidth={LINE} strokeLinejoin="round" />
      ) : null}
      {values.map((value, i) =>
        value === null || xs[i] === undefined ? null : (
          <circle key={i} data-mark="point" data-week={i + 1} data-x={xs[i]} cx={xs[i]} cy={y(value)} r={POINT / 2} fill={colour("ink")} />
        ),
      )}
    </svg>
  );
}
