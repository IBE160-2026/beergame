"use client";

import { type RefObject, useLayoutEffect, useState } from "react";

export type BoxSize = { width: number; fontSize: number };

/** The box's width and font size in px, measured again when it resizes (text zoom, a font
 * loading, the breakpoint). A chart takes them as fixed sizes (AD-18); until the box is measured
 * (a server render) `fallback` stands. */
export function useBoxSize(box: RefObject<HTMLElement | null>, fallback: BoxSize): BoxSize {
  const [size, setSize] = useState(fallback);
  useLayoutEffect(() => {
    const element = box.current;
    if (!element) return;
    const measure = () => {
      const width = Math.floor(element.clientWidth);
      const fontSize = parseFloat(getComputedStyle(element).fontSize) || fallback.fontSize;
      if (width > 0) setSize((was) => (was.width === width && was.fontSize === fontSize ? was : { width, fontSize }));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [box, fallback.fontSize]);
  return size;
}
