import NextLink from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type StegeneState = "done" | "current" | "locked";

export type StegeneItem = {
  key: string;
  /** The step's name: «Klassespill». */
  name: string;
  state: StegeneState;
  /** The state in words: «pågår» for the current step, «ferdig» for a done one, and for a later
   * step the line that says what opens it («Replay, åpnes når du har bestått Debrief-quizen.»). */
  note: string;
  /** Where the current step leads (Story 9.2: the Debrief); its name is then a link. */
  href?: string;
  /** Story 13.7: an action under an open step's row (the Student report's download); Story 13.9:
   * also under a locked one (the deletion date under «Rapport»). */
  action?: ReactNode;
};

/**
 * Stegene (UX-DR29, DESIGN.md → Stegene, mockup `04-student-hjem.png`): the Student's steps as an
 * ordered list joined by a thin line. The current step has a filled marker, its name in `ink` and
 * «pågår» in text; a done step a filled marker and «ferdig»; a later step a hollow marker and the
 * line that says what opens it, in `ink-secondary`. The markers are decorative: the state is
 * always in words, never in colour or shape alone. The component holds no rule for which step is
 * open; the api decides and the caller passes the words. A current step with `href` (the
 * Debrief, Story 9.2) names itself as a Lenke to it. A step with `action` (Story 13.7: the Student
 * report's download under «Rapport») shows it under its row. Reused by Epics 9 to 13.
 */
export function Stegene({ title, items, titleId }: { title: string; items: StegeneItem[]; titleId: string }) {
  return (
    <section aria-labelledby={titleId} className="mt-6">
      <h3 id={titleId} className="text-label font-semibold text-ink">
        {title}
      </h3>
      <ol className="mt-2 flex flex-col">
        {items.map((item, index) => (
          <li key={item.key} data-state={item.state} className="relative flex gap-3 pb-2 last:pb-0">
            {index < items.length - 1 ? (
              // From under this marker to the top of the next one, centred on the marker at any text size.
              <span
                aria-hidden="true"
                className="absolute top-[1.125rem] -bottom-1.5 left-[calc(0.375rem-0.5px)] border-l border-axis"
              />
            ) : null}
            <svg aria-hidden="true" viewBox="0 0 12 12" className="relative mt-1.5 size-3 shrink-0">
              <circle
                cx="6"
                cy="6"
                r="5"
                strokeWidth="1.5"
                className={item.state === "locked" ? "fill-paper stroke-axis" : "fill-ink stroke-ink"}
              />
            </svg>
            {item.state === "locked" ? (
              item.action ? (
                <div className="flex flex-1 flex-col">
                  <span className="text-body-phone text-ink-secondary lg:text-body">{item.note}</span>
                  {item.action}
                </div>
              ) : (
                <span className="text-body-phone text-ink-secondary lg:text-body">{item.note}</span>
              )
            ) : (
              <div className="flex flex-1 flex-col">
                <span className="flex flex-wrap justify-between gap-x-4 text-body-phone lg:text-body">
                  {item.href ? (
                    // A Lenke (DESIGN.md → Controls): `lager`, weight 600, underlined. Padding taken
                    // back by a negative margin gives it a 44 px tap target without moving the row.
                    <NextLink
                      href={item.href}
                      className="-my-3.5 inline-block py-3.5 font-semibold text-lager underline underline-offset-2 hover:decoration-2 active:text-ink"
                    >
                      {item.name}
                    </NextLink>
                  ) : (
                    <span className={cn("text-ink", item.state === "current" && "font-semibold")}>{item.name}</span>
                  )}
                  <span className="text-ink-secondary">{item.note}</span>
                </span>
                {item.action}
              </div>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
