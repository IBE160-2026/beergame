"use client";

import { useId, useRef } from "react";

import { MatrixWall } from "@/components/charts/matrix-wall";
import { nb } from "@/copy/nb";
import { useBoxSize } from "@/lib/box-size";
import { formatCell, wallCopy } from "@/modules/games/wall-copy";

import { demoWallGroups } from "./demo-wall";

const copy = nb.landing;
/** Until the box is measured (a server render): a phone column and the caption size. */
const FALLBACK = { width: 288, fontSize: 13 };

/**
 * «Alle spillene på én skjerm» (Story 7.2, UX-DR70): the shared Matrisevegg fed with bundled
 * Demodata, no api call, labelled «Demodata». No names, no Uke per row, no Uke total (UX-DR71).
 */
export function WallFigure() {
  const id = useId();
  const box = useRef<HTMLDivElement>(null);
  const size = useBoxSize(box, FALLBACK);
  return (
    <section aria-labelledby={id} className="mt-12 border-t border-hairline pt-8 lg:mt-16" data-landing-wall="">
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 id={id} className="text-headline text-ink">
          {copy.wall.title}
        </h2>
        <p className="text-caption text-ink-secondary">{copy.seat.demoData}</p>
      </div>
      <p className="mt-2 max-w-prose text-body-phone text-ink-secondary lg:text-body">{copy.wall.lead}</p>
      <div ref={box} className="mt-4 min-w-0 text-caption lg:max-w-3xl">
        <MatrixWall
          width={size.width}
          fontSize={size.fontSize}
          groups={demoWallGroups()}
          copy={wallCopy(null, false)}
          format={formatCell}
          maxHeight="none"
        />
      </div>
    </section>
  );
}
