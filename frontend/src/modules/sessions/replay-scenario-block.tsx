import { useId } from "react";

import { nb } from "@/copy/nb";

import type { ClassSession } from "./api";
import { hiddenLine, scenarioRows } from "./replay-scenario";

const copy = nb.sessions.replay;

/**
 * The Klasseøkt's «Replay-scenario» (Story 10.1, FR-49, FR-72): the default scenario, the only
 * choice so far, named and described in words from the template the api derives from the Game
 * settings (or froze at the lock). The Lecturer sees the ranges; the Students never see the
 * values drawn for them. Read-only: Story 10.2 adds the choice of an own scenario.
 */
export function ReplayScenarioBlock({ item }: { item: ClassSession }) {
  const titleId = useId();
  const template = item.replay_template;
  return (
    <section aria-labelledby={titleId} className="mt-12 max-w-2xl border-t border-hairline pt-6" data-replay-scenario="">
      <h2 id={titleId} className="text-label text-ink">
        {copy.title}
      </h2>
      <p className="mt-2 text-body-phone text-ink lg:text-body">{copy.standard}</p>
      <dl className="mt-4">
        {scenarioRows(template).map((row) => (
          <div
            key={row.label}
            className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-hairline py-2"
          >
            <dt className="text-body-phone text-ink lg:text-body">{row.label}</dt>
            <dd className="text-right text-body-phone font-semibold text-ink tabular-nums lg:text-body">{row.value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-body-phone text-ink-secondary">{hiddenLine(template)}</p>
    </section>
  );
}
