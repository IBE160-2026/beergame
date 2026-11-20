"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { Link } from "@/components/link";
import { SelectField } from "@/components/select-field";
import { Switch } from "@/components/switch";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";
import { formatTime } from "@/modules/admin/audit";
import { LINK_BUTTON } from "@/modules/classes/roster-entry-forms";
import { classSessionPath } from "@/modules/identity/homes";

import {
  classSessionKey,
  classSessionsKey,
  copyClassSession,
  createClassSession,
  useClassSessions,
  useCopySources,
} from "./api";
import { sourceGroups, sourceLabel } from "./rerun";

const copy = nb.sessions.list;

/**
 * «Klasseøkter» on the Klasse page (Story 5.1): the Class's sessions, newest first, each a Lenke to
 * its Klasseøkt with whether it has been saved. «Lag Klasseøkt» creates one filled in with the
 * Classic defaults and opens it; it is shown only to the Class's Faglærere while the Class is
 * active (an Assistant lecturer never sees it, FR-5). With `FEATURE_RERUN` on, the Lenke «Lag fra
 * en tidligere Klasseøkt» opens a panel in place to copy an earlier one (Story 5.18).
 */
export function ClassSessions({ classId, canCreate }: { classId: string; canCreate: boolean }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const sessions = useClassSessions(classId);
  const action = useAction({
    mutationFn: () => createClassSession(classId),
    fallback: copy.createFailed,
    onSuccess: (created) => {
      queryClient.setQueryData(classSessionKey(created.id), created);
      void queryClient.invalidateQueries({ queryKey: classSessionsKey(classId), exact: true });
      void queryClient.invalidateQueries({ queryKey: ["class-sessions", "copy-sources"] });
      router.push(classSessionPath(created.id));
    },
  });
  const items = sessions.data?.items;
  const [copying, setCopying] = useState(false);
  const openRef = useRef<HTMLButtonElement>(null);
  const wasCopying = useRef(false);
  useEffect(() => {
    // Closed again: focus returns to the Lenke that opened it.
    if (wasCopying.current && !copying) openRef.current?.focus();
    wasCopying.current = copying;
  }, [copying]);
  return (
    <section aria-labelledby="class-sessions-title" className="mt-10">
      <h2 id="class-sessions-title" className="text-headline text-ink">
        {copy.title}
      </h2>
      {sessions.isError ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
          <p className="text-body-phone text-ink lg:text-body">{nb.system.pageError}</p>
          <Button onClick={() => void sessions.refetch()}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {items && items.length === 0 ? (
        <p className="mt-2 text-body-phone text-ink-secondary lg:text-body">{copy.empty}</p>
      ) : null}
      {items && items.length > 0 ? (
        <ul className="mt-2 max-w-2xl">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col items-start border-b border-hairline pb-2 sm:flex-row sm:items-baseline sm:justify-between sm:gap-x-4 sm:py-1">
              <Link href={classSessionPath(item.id)} standalone>
                {copy.item(item.number, formatTime(item.created_at))}
              </Link>
              <span className="text-body-phone text-ink-secondary">{item.saved_at ? copy.saved : copy.unsaved}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {canCreate ? (
        <div className="mt-4 flex flex-col items-start gap-2">
          <Button
            unavailable={action.isPending || action.isSuccess}
            onClick={() => {
              if (!action.isPending && !action.isSuccess) action.mutate();
            }}
          >
            {action.isPending || action.isSuccess ? copy.creating : copy.create}
          </Button>
          <ActionError message={action.errorMessage} />
          {sessions.data?.rerun_enabled && !copying ? (
            <button ref={openRef} type="button" className={LINK_BUTTON} onClick={() => setCopying(true)}>
              {copy.rerun.open}
            </button>
          ) : null}
          {sessions.data?.rerun_enabled && copying ? (
            <CopyPanel classId={classId} onClose={() => setCopying(false)} />
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

/**
 * «Lag fra en tidligere Klasseøkt» (Story 5.18, cut list, FR-66): opened in place, with focus on its
 * first field. The Faglærer picks one of the Class sessions the api offers (any Class they are staff
 * of), chooses whether to keep the demand seed with a Bryter, and «Lag kopi» makes the new Class
 * session in this Class and opens it. What is and is not copied stands above the button.
 */
function CopyPanel({ classId, onClose }: { classId: string; onClose: () => void }) {
  const r = copy.rerun;
  const router = useRouter();
  const queryClient = useQueryClient();
  const ids = useId();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const sources = useCopySources(classId, true);
  const [chosen, setChosen] = useState("");
  const [keepSeed, setKeepSeed] = useState(false);
  const sourceRef = useRef<HTMLSelectElement>(null);
  const items = sources.data?.items;
  // Focus goes to the first field (EXPERIENCE.md, GitHub issue 116); until the sources are there,
  // or when there are none, to the heading. Once the field shows, it takes focus only from the
  // heading, never from where the User has moved on to.
  const hasSources = (items?.length ?? 0) > 0;
  useEffect(() => titleRef.current?.focus(), []);
  useEffect(() => {
    if (hasSources && (document.activeElement === titleRef.current || document.activeElement === document.body)) {
      sourceRef.current?.focus();
    }
  }, [hasSources]);
  const sourceId = chosen || items?.[0]?.id || "";
  const action = useAction({
    mutationFn: () => copyClassSession(classId, sourceId, keepSeed),
    fallback: r.failed,
    messages: { invalid_settings: r.refused },
    onSuccess: (created) => {
      queryClient.setQueryData(classSessionKey(created.id), created);
      void queryClient.invalidateQueries({ queryKey: classSessionsKey(classId), exact: true });
      void queryClient.invalidateQueries({ queryKey: ["class-sessions", "copy-sources"] });
      router.push(classSessionPath(created.id));
    },
  });
  const busy = action.isPending || action.isSuccess;
  return (
    <section
      aria-labelledby={`${ids}-title`}
      className="mt-2 flex w-full max-w-xl flex-col items-start gap-4 rounded-sm border border-ink-muted px-4 py-4"
    >
      <h3
        id={`${ids}-title`}
        ref={titleRef}
        tabIndex={-1}
        className="w-full border-b border-hairline pb-3 text-body-phone font-semibold text-ink focus:outline-none lg:text-body"
      >
        {r.title}
      </h3>
      {sources.isError ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <p className="text-body-phone text-ink lg:text-body">{r.loadFailed}</p>
          <Button onClick={() => void sources.refetch()}>{nb.system.retry}</Button>
        </div>
      ) : null}
      {sources.isPending ? <p className="text-body-phone text-ink-secondary">{nb.system.loading}</p> : null}
      {items && items.length === 0 ? <p className="text-body-phone text-ink lg:text-body">{r.none}</p> : null}
      {items && items.length > 0 ? (
        <>
          <SelectField
            id={`${ids}-source`}
            ref={sourceRef}
            label={r.source}
            value={sourceId}
            onChange={(event) => setChosen(event.target.value)}
            className="w-full"
          >
            {sourceGroups(items).map((group) => (
              <optgroup key={group.classId} label={group.label}>
                {group.items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {sourceLabel(item)}
                  </option>
                ))}
              </optgroup>
            ))}
          </SelectField>
          <div className="flex flex-col gap-1">
            <p id={`${ids}-seed`} className="text-label text-ink">
              {r.keepSeed}
            </p>
            <Switch
              id={`${ids}-seed-switch`}
              checked={keepSeed}
              onChange={setKeepSeed}
              labelledBy={`${ids}-seed`}
              describedBy={`${ids}-seed-help`}
            >
              {keepSeed ? r.keepSeedOn : r.keepSeedOff}
            </Switch>
            <p id={`${ids}-seed-help`} className="text-body-phone text-ink-secondary">
              {r.keepSeedHelp}
            </p>
          </div>
          <div className="text-body-phone text-ink-secondary">
            <p>{r.copied}</p>
            <p>{r.notCopied}</p>
          </div>
        </>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        {items && items.length > 0 ? (
          <Button
            variant="primary"
            unavailable={busy}
            onClick={() => {
              if (!busy && sourceId) action.mutate();
            }}
          >
            {busy ? r.submitting : r.submit}
          </Button>
        ) : null}
        <Button onClick={onClose}>{r.cancel}</Button>
      </div>
      <ActionError message={action.errorMessage} />
    </section>
  );
}
