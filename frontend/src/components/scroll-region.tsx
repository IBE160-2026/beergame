"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * A region that scrolls sideways on its own while the page never does (UX-DR75): a diagram wider
 * than the screen keeps its natural width and readable labels. A phone shows that the region
 * scrolls (Issue #98) without fades or gradients (DESIGN.md): the week table's visible thin
 * scrollbar under the content, and a 1 px `axis` hairline on each side that has more to show,
 * where the content is cut (Epic 7 close-out; this replaces the fade to `paper`). The region takes
 * focus, so it scrolls from the keyboard, and is named by `labelledBy`. `scrollClassName` adds to
 * the scrolling element, e.g. a height cap that lets a long table scroll down inside the region.
 */
export function ScrollRegion({
  labelledBy,
  className,
  scrollClassName,
  children,
}: {
  labelledBy: string;
  className?: string;
  scrollClassName?: string;
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
        className={cn(
          "overflow-x-auto pb-1 [scrollbar-color:var(--color-ink-muted)_var(--color-hairline)] [scrollbar-width:thin] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
          scrollClassName,
        )}
      >
        {children}
      </div>
      <div
        aria-hidden="true"
        data-more="left"
        data-visible={more.left}
        className={cn("pointer-events-none absolute inset-y-0 left-0 border-l border-axis", more.left ? "block" : "hidden")}
      />
      <div
        aria-hidden="true"
        data-more="right"
        data-visible={more.right}
        className={cn("pointer-events-none absolute inset-y-0 right-0 border-l border-axis", more.right ? "block" : "hidden")}
      />
    </div>
  );
}
