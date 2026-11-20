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
};

/**
 * Stegene (UX-DR29, DESIGN.md → Stegene, mockup `04-student-hjem.png`): the Student's steps as an
 * ordered list joined by a thin line. The current step has a filled marker, its name in `ink` and
 * «pågår» in text; a done step a filled marker and «ferdig»; a later step a hollow marker and the
 * line that says what opens it, in `ink-secondary`. The markers are decorative: the state is
 * always in words, never in colour or shape alone. The component holds no rule for which step is
 * open; the api decides and the caller passes the words. Reused by Epics 9 to 13.
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
              <span aria-hidden="true" className="absolute top-4 bottom-0 left-[5px] border-l border-axis" />
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
              <span className="text-body-phone text-ink-secondary lg:text-body">{item.note}</span>
            ) : (
              <span className="flex flex-1 flex-wrap justify-between gap-x-4 text-body-phone lg:text-body">
                <span className={cn("text-ink", item.state === "current" && "font-semibold")}>{item.name}</span>
                <span className="text-ink-secondary">{item.note}</span>
              </span>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
