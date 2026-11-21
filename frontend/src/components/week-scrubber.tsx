"use client";

import { type KeyboardEvent, type PointerEvent, useRef } from "react";

import { Button } from "@/components/button";
import { cn } from "@/lib/utils";

/** The keys of the Ukeskrubber and the step each takes (EXPERIENCE.md → Ukeskrubber). */
export function scrubKey(key: string, value: number, last: number): number | null {
  const clamp = (week: number) => Math.max(1, Math.min(last, week));
  switch (key) {
    case "ArrowLeft":
    case "ArrowDown":
      return clamp(value - 1);
    case "ArrowRight":
    case "ArrowUp":
      return clamp(value + 1);
    case "PageDown":
      return clamp(value - 4);
    case "PageUp":
      return clamp(value + 4);
    case "Home":
      return 1;
    case "End":
      return last;
    default:
      return null;
  }
}

/**
 * Ukeskrubber (Story 9.5, UX-DR34, DESIGN.md `scrubber`, EXPERIENCE.md → Ukeskrubber): a thin track
 * from «Uke 1» to the last Uke, `ink` up to the handle and `ink-muted` after it, the `ink` handle
 * with its «Uke 15» above. A `role="slider"` named «Velg uke»: Left/Down −1, Right/Up +1,
 * PageDown/PageUp ±4, Home/End the first and last Uke. Two outlined step buttons of at least 44 px
 * («Én uke tilbake», «Én uke fram») stand at the ends, so no task needs a drag; a drag or a press
 * on the track moves it too. Shared, for the Debrief and later the shared screen and Replay.
 */
export function WeekScrubber({
  value,
  last,
  onChange,
  label,
  weekText,
  back,
  forward,
}: {
  /** The chosen Uke, 1 to `last`. */
  value: number;
  last: number;
  onChange: (week: number) => void;
  /** «Velg uke». */
  label: string;
  /** «Uke 15»: the value text and the labels at the ends and on the handle. */
  weekText: (week: number) => string;
  /** «Én uke tilbake», «Én uke fram»: the step buttons' names. */
  back: string;
  forward: string;
}) {
  const track = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const share = last > 1 ? (value - 1) / (last - 1) : 1;
  const set = (week: number) => {
    if (week !== value) onChange(week);
  };
  const fromPointer = (event: PointerEvent<HTMLDivElement>) => {
    const box = track.current?.getBoundingClientRect();
    if (!box || box.width <= 0) return;
    const at = Math.max(0, Math.min(1, (event.clientX - box.left) / box.width));
    set(Math.round(at * (last - 1)) + 1);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    // Browser and screen reader shortcuts (Alt+Left is «back») pass through.
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const next = scrubKey(event.key, value, last);
    if (next === null) return;
    event.preventDefault();
    set(next);
  };
  const percent = `${share * 100}%`;
  return (
    <div data-scrubber="" className="flex items-center gap-2">
      <Button
        aria-label={back}
        unavailable={value <= 1}
        onClick={() => set(Math.max(1, value - 1))}
        className="min-h-tap-target-min min-w-tap-target-min px-0"
      >
        <span aria-hidden="true">−</span>
      </Button>
      <div className="min-w-0 flex-1 px-2">
        {/* The handle's own label rides above it, kept inside the track's ends. */}
        <div className="relative h-[1.6em] text-caption text-ink" aria-hidden="true">
          <span
            className="absolute bottom-0 font-semibold whitespace-nowrap tabular-nums"
            style={{ left: percent, transform: `translateX(-${share * 100}%)` }}
          >
            {weekText(value)}
          </span>
        </div>
        <div
          ref={track}
          role="slider"
          tabIndex={0}
          aria-label={label}
          aria-valuemin={1}
          aria-valuemax={last}
          aria-valuenow={value}
          aria-valuetext={weekText(value)}
          aria-orientation="horizontal"
          onKeyDown={onKeyDown}
          onPointerDown={(event) => {
            if (event.button !== 0) return; // the main button, a touch or a pen only
            dragging.current = true;
            event.currentTarget.setPointerCapture?.(event.pointerId);
            fromPointer(event);
          }}
          onPointerMove={(event) => {
            if (dragging.current) fromPointer(event);
          }}
          onPointerUp={() => {
            dragging.current = false;
          }}
          onPointerCancel={() => {
            dragging.current = false;
          }}
          className={cn(
            "relative h-tap-target-min cursor-pointer touch-none rounded-sm",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
          )}
        >
          {/* Marks drawn as borders, so none of them is a text background. */}
          <span aria-hidden="true" className="absolute top-1/2 right-0 left-0 h-0 -translate-y-1/2 border-t-2 border-ink-muted" />
          <span aria-hidden="true" className="absolute top-1/2 left-0 h-0 -translate-y-1/2 border-t-2 border-ink" style={{ width: percent }} />
          <span
            aria-hidden="true"
            data-handle=""
            className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-8 border-ink outline-2 outline-paper"
            style={{ left: percent }}
          />
        </div>
        <div aria-hidden="true" className="flex justify-between text-caption text-ink-secondary tabular-nums">
          <span>{weekText(1)}</span>
          <span>{weekText(last)}</span>
        </div>
      </div>
      <Button
        aria-label={forward}
        unavailable={value >= last}
        onClick={() => set(Math.min(last, value + 1))}
        className="min-h-tap-target-min min-w-tap-target-min px-0"
      >
        <span aria-hidden="true">+</span>
      </Button>
    </div>
  );
}
