"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * A region that scrolls sideways on its own while the page never does (UX-DR75): a diagram wider
 * than the screen keeps its natural width and readable labels. Each side that has more to show
 * fades out into `paper`, so a phone shows that the region scrolls (Issue #98). The region takes
 * focus, so it scrolls from the keyboard, and is named by `labelledBy`.
 */
export function ScrollRegion({
  labelledBy,
  className,
  children,
}: {
  labelledBy: string;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [more, setMore] = useState({ left: false, right: false });
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => {
      const left = element.scrollLeft > 1;
      const right = element.scrollLeft + element.clientWidth < element.scrollWidth - 1;
      setMore((was) => (was.left === left && was.right === right ? was : { left, right }));
    };
    update();
    element.addEventListener("scroll", update, { passive: true });
    const observer = new ResizeObserver(update);
    observer.observe(element);
    if (element.firstElementChild) observer.observe(element.firstElementChild);
    return () => {
      element.removeEventListener("scroll", update);
      observer.disconnect();
    };
  }, []);
  return (
    <div className={cn("relative", className)}>
      <div
        ref={ref}
        role="group"
        aria-labelledby={labelledBy}
        tabIndex={0}
        className="overflow-x-auto focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
      >
        {children}
      </div>
      <div
        aria-hidden="true"
        data-fade="left"
        data-visible={more.left}
        className={cn(
          "pointer-events-none absolute inset-y-0 left-0 w-10 bg-linear-to-r from-paper to-transparent transition-opacity motion-reduce:transition-none",
          more.left ? "opacity-100" : "opacity-0",
        )}
      />
      <div
        aria-hidden="true"
        data-fade="right"
        data-visible={more.right}
        className={cn(
          "pointer-events-none absolute inset-y-0 right-0 w-10 bg-linear-to-l from-paper to-transparent transition-opacity motion-reduce:transition-none",
          more.right ? "opacity-100" : "opacity-0",
        )}
      />
    </div>
  );
}
