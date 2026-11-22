"use client";

import { useId } from "react";

import { Switch } from "@/components/switch";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import type { ClassSession } from "@/modules/sessions/api";

import type { SittingDraft } from "./sitting";

const copy = nb.tests.sitting;
const LINE = "text-body-phone lg:text-body";

/**
 * «Tidsgrense på testen» on the Klasseøkt (Story 11.12, FR-51, UX-DR12, UX-DR49): a Bryter that
 * requires the Individual test in one sitting, and while it is on a Tekstfelt for the limit in
 * whole minutes with its scope and range under it. It changes a draft that takes effect on
 * «Lagre Klasseøkt»; from the Start date, and for an Assistant lecturer, it stands as text. The
 * state is in words beside the track, never by colour alone.
 */
export function TimedSittingBlock({
  item,
  draft,
  error,
  onChange,
  onLeave,
}: {
  item: ClassSession;
  draft: SittingDraft;
  /** The minutes field's reason, from the web's check or the api's refusal. */
  error?: string;
  onChange: (draft: SittingDraft) => void;
  onLeave: () => void;
}) {
  const ids = useId();
  const titleId = `${ids}-title`;
  const leadId = `${ids}-lead`;
  const state = item.test_sitting;
  // The api's own word, held to the page's: frozen with the choices from the Start date.
  const editable = state.can_change && item.can_manage && !item.locked;
  return (
    <section aria-labelledby={titleId} className="mt-12 max-w-2xl border-t border-hairline pt-8" data-test-sitting="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.heading}
      </h2>
      <p id={leadId} className={`${LINE} mt-2 text-ink-secondary`}>
        {copy.lead}
      </p>
      {editable ? (
        <>
          <Switch
            id={`${ids}-switch`}
            className="mt-3"
            checked={draft.on}
            onChange={(on) => onChange({ ...draft, on })}
            labelledBy={titleId}
            describedBy={leadId}
          >
            {draft.on ? copy.on : copy.off}
          </Switch>
          {draft.on ? (
            <TextField
              id={`${ids}-minutes`}
              className="mt-4 max-w-xs"
              label={copy.minutesLabel}
              inputMode="numeric"
              autoComplete="off"
              value={draft.minutes}
              onChange={(event) => onChange({ ...draft, minutes: event.target.value })}
              onBlur={onLeave}
              hint={copy.range(state.min_minutes, state.max_minutes)}
              error={error}
              errorAlert
            />
          ) : null}
          <p className={`${LINE} mt-3 text-ink-secondary`}>{copy.help}</p>
        </>
      ) : (
        <>
          <p className={`${LINE} mt-3 font-semibold text-ink`}>
            {state.minutes !== null ? copy.readOnly(state.minutes) : copy.readOnlyOff}
          </p>
          {state.minutes !== null ? <p className={`${LINE} mt-2 text-ink-secondary`}>{copy.help}</p> : null}
          {item.locked ? <p className={`${LINE} mt-2 text-ink`}>{copy.locked}</p> : null}
        </>
      )}
    </section>
  );
}
