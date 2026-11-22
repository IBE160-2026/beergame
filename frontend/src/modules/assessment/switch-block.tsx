"use client";

import { useId } from "react";

import { Switch } from "@/components/switch";
import { nb } from "@/copy/nb";
import type { ClassSession } from "@/modules/sessions/api";
import { osloDateText } from "@/modules/sessions/dates";

const copy = nb.assessment.switchBlock;

/**
 * «KI-vurdering» on the Klasseøkt (Story 12.1, FR-61, UX-DR49): the Bryter that switches the AI
 * assessment of the Individual test off for this Class session, on by default. It changes a draft
 * that takes effect on «Lagre Klasseøkt», also after the Start date, until the original Test
 * deadline; then the Test-deadline lock pins it and it stands as text with the time it was locked.
 * An Assistant lecturer reads it as text (AD-12). The state is in words beside the track, never by
 * colour alone (UX-DR12).
 */
export function AiAssessmentBlock({
  item,
  draft,
  onChange,
}: {
  item: ClassSession;
  draft: boolean;
  onChange: (enabled: boolean) => void;
}) {
  const ids = useId();
  const titleId = `${ids}-title`;
  const helpId = `${ids}-help`;
  const leadId = `${ids}-lead`;
  const state = item.ai_assessment;
  const editable = state.can_change;
  const shown = editable ? draft : state.enabled;
  return (
    <section aria-labelledby={titleId} className="mt-12 max-w-2xl border-t border-hairline pt-8" data-ai-assessment="">
      <h2 id={titleId} className="text-headline text-ink">
        {copy.title}
      </h2>
      <p id={leadId} className="mt-2 text-body-phone text-ink-secondary lg:text-body">
        {copy.lead}
      </p>
      {editable ? (
        <Switch
          id={`${ids}-switch`}
          className="mt-3"
          checked={draft}
          onChange={onChange}
          labelledBy={titleId}
          describedBy={`${leadId} ${helpId}`}
        >
          {draft ? copy.on : copy.off}
        </Switch>
      ) : (
        <p className="mt-3 text-body-phone font-semibold text-ink lg:text-body">{shown ? copy.on : copy.off}</p>
      )}
      <p id={helpId} className="mt-2 text-body-phone text-ink-secondary lg:text-body">
        {copy.help}
      </p>
      <p className="mt-2 text-body-phone text-ink lg:text-body">
        {state.pinned_at
          ? copy.pinned(osloDateText(state.pinned_at))
          : state.open
            ? copy.open
            : copy.deadlinePassed}
      </p>
    </section>
  );
}
