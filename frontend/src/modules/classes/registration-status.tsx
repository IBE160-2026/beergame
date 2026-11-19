"use client";

import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, type Ref, useEffect, useRef, useState } from "react";

import { ActionError } from "@/components/action-error";
import { Button } from "@/components/button";
import { SelectField } from "@/components/select-field";
import { TextField } from "@/components/text-field";
import { nb } from "@/copy/nb";
import { useAction } from "@/lib/api/mutation";

import {
  invitationSummaryKey,
  type Registration,
  type Registrations,
  type RegistrationStatus as Status,
  type RemindersSent,
  registrationsKey,
  sendReminders,
  useRegistrations,
} from "./api";
import { useFormArea } from "./one-form";
import { barShares, filterRegistrations, reminderReach, STATUSES, statusLabel } from "./registration";
import { EntryResult, ManualForm, RemoveConfirm, resultText } from "./roster-entry-forms";
import { dayLabel, parseValidDays, VALID_DAYS } from "./roster";

const copy = nb.classes.registration;

const LINK_BUTTON =
  "inline-flex min-h-tap-target-min min-w-tap-target-min cursor-pointer items-center text-label text-lager underline underline-offset-2 hover:decoration-2 active:text-ink";

/** Who a reminder goes to: every address that has not registered, or one. */
type Target = { kind: "all" } | { kind: "one"; item: Registration };

/** The row form that is open (Story 4.8): «Registrer manuelt» or «Fjern» for one address. */
type RowAction = { kind: "manual" | "remove"; item: Registration };

const entries = nb.classes.entries;

function isRegistered(item: Registration): boolean {
  return item.status === "registered" || item.status === "registered_manually";
}

/** The outcome the result line states, with the address of a single resend. */
type Outcome = { sent: RemindersSent; address: string | null; first: boolean };

/** A row that has had no Invitation yet («Ikke invitert ennå», Story 4.8) gets its first one, so
 * its action never says «ny» (Issue #91). */
const isFirst = (item: Registration) => item.status === "not_invited";

/**
 * «Status etter utsending» on the Class page (Story 4.7, FR-9, NFR-10, UX-DR47). As mockup 02:
 * one bar of the Roster in registered, registered manually and unregistered, with the totals as
 * text beside their keys, and the Lenke «Send påminnelse til N». The Lenke opens an in-place
 * confirmation with the validity prefilled with 14 days. Under it, every address with its status
 * in text, filtered by status and searched by address, each that may get one with «Send ny
 * Invitasjon», which opens the same confirmation for that address alone. The result line names
 * how many reminders went out and the hard-bounced addresses left out.
 */
export function RegistrationStatus({ classId, readOnly = false }: { classId: string; readOnly?: boolean }) {
  const found = useRegistrations(classId);
  if (found.isPending) return null;
  const data = found.data;
  if (data && data.items.length === 0) return null;
  return (
    <section aria-labelledby="registration-title" className="mt-10">
      <h2 id="registration-title" className="text-headline text-ink">
        {copy.title}
      </h2>
      <div className="mt-4">
        {!data ? (
          <p role="alert" className="text-body-phone text-restordre lg:text-body">
            {copy.failed}
          </p>
        ) : (
          <StatusView classId={classId} data={data} readOnly={readOnly} />
        )}
      </div>
    </section>
  );
}

/** `readOnly`: an Assistant lecturer reads the list (Story 4.9) and gets no reminder or row
 * action, which the api would refuse. */
function StatusView({ classId, data, readOnly }: { classId: string; data: Registrations; readOnly: boolean }) {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<Target | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [rowAction, setRowAction] = useState<RowAction | null>(null);
  // Archived while a reminder or row form was open (Story 4.10): it closes with the actions.
  useEffect(() => {
    if (!readOnly) return;
    setTarget(null);
    setRowAction(null);
  }, [readOnly]);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeLine = useRef<HTMLParagraphElement>(null);
  const [focusNotice, setFocusNotice] = useState(false);
  useEffect(() => {
    if (focusNotice && noticeLine.current) {
      noticeLine.current.focus();
      setFocusNotice(false);
    }
  }, [focusNotice, notice]);
  const resultLine = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const [focusResult, setFocusResult] = useState(false);
  useEffect(() => {
    if (focusResult && resultLine.current) {
      resultLine.current.focus();
      setFocusResult(false);
    }
  }, [focusResult, outcome]);

  const remind = useAction({
    mutationFn: ({ days, entryId }: { days: number; entryId?: string }) => sendReminders(classId, days, entryId),
    messages: {
      nothing_to_send: copy.nothingToSend,
      invalid_request: nb.classes.roster.validDaysError(VALID_DAYS.min, VALID_DAYS.max),
    },
    fallback: copy.sendFailed,
    onSuccess: (sent, vars) => {
      const row = vars.entryId ? data.items.find((i) => i.id === vars.entryId) : undefined;
      setOutcome({ sent, address: row?.email ?? null, first: row ? isFirst(row) : false });
      setTarget(null);
      setFocusResult(true);
      void queryClient.invalidateQueries({ queryKey: registrationsKey(classId), exact: true });
      void queryClient.invalidateQueries({ queryKey: invitationSummaryKey(classId), exact: true });
    },
  });

  // Another area's form closes this one and clears the result lines (one form on the page); a
  // reminder being sent keeps its confirmation until it answers.
  const take = useFormArea("status", () => {
    setOutcome(null);
    setNotice(null);
    setRowAction(null);
    if (!remind.isPending) {
      remind.reset();
      setTarget(null);
    }
  });
  const open = (next: Target, from: HTMLButtonElement) => {
    // A new action clears the last result line and refusal, and closes any other form.
    setOutcome(null);
    setNotice(null);
    setRowAction(null);
    remind.reset();
    opener.current = from;
    setTarget(next);
    take();
  };
  const openRow = (next: RowAction, from: HTMLButtonElement) => {
    if (remind.isPending) return;
    setOutcome(null);
    setNotice(null);
    setTarget(null);
    remind.reset();
    opener.current = from;
    setRowAction(next);
    take();
  };
  const closeRow = () => {
    setRowAction(null);
    opener.current?.focus();
  };
  const rowDone = (text: string) => {
    setRowAction(null);
    setNotice(text);
    setFocusNotice(true);
  };
  const rowPanel = (action: RowAction) =>
    action.kind === "manual" ? (
      <ManualForm
        key={`manual-${action.item.id}`}
        classId={classId}
        from={{ email: action.item.email, entryId: action.item.id }}
        idPrefix={`manual-${action.item.id}`}
        onDone={(registration) => rowDone(resultText("manual", registration))}
        onCancel={closeRow}
      />
    ) : (
      <RemoveConfirm
        key={`remove-${action.item.id}`}
        classId={classId}
        item={action.item}
        onDone={rowDone}
        onCancel={closeRow}
      />
    );
  const close = () => {
    if (remind.isPending) return;
    remind.reset();
    setTarget(null);
    opener.current?.focus();
  };

  const confirm = (forTarget: Target) => (
    <Confirm
      key={forTarget.kind === "all" ? "all" : forTarget.item.id}
      target={forTarget}
      items={data.items}
      sending={remind.isPending}
      error={remind.errorMessage}
      onEdit={() => {
        if (remind.isError) remind.reset();
      }}
      onCancel={close}
      onSend={(days) =>
        remind.mutate({ days, entryId: forTarget.kind === "one" ? forTarget.item.id : undefined })
      }
    />
  );

  return (
    <div className="flex flex-col gap-6">
      <Totals
        data={data}
        onRemindAll={(button) => open({ kind: "all" }, button)}
        remindOpen={target?.kind === "all"}
        readOnly={readOnly}
      />
      {target?.kind === "all" ? confirm(target) : null}
      {outcome ? <Result outcome={outcome} ref={resultLine} /> : null}
      {notice ? <EntryResult text={notice} ref={noticeLine} /> : null}
      <AddressList
        items={data.items}
        open={
          target?.kind === "one"
            ? { id: target.item.id, kind: "resend" }
            : rowAction
              ? { id: rowAction.item.id, kind: rowAction.kind }
              : null
        }
        panel={target?.kind === "one" ? confirm(target) : rowAction ? rowPanel(rowAction) : null}
        onResend={(item, button) => open({ kind: "one", item }, button)}
        onManual={(item, button) => openRow({ kind: "manual", item }, button)}
        onRemove={(item, button) => openRow({ kind: "remove", item }, button)}
        readOnly={readOnly}
        onFilter={() => {
          // A row's form would vanish with its row: close it with the old view.
          if (target?.kind === "one" && !remind.isPending) {
            remind.reset();
            setTarget(null);
          }
          setRowAction(null);
        }}
      />
    </div>
  );
}

/** The bar and its keys with the totals as text (mockup 02); the bar repeats the text and is
 * hidden from screen readers. */
function Totals({
  data,
  onRemindAll,
  remindOpen,
  readOnly,
}: {
  data: Registrations;
  onRemindAll: (button: HTMLButtonElement) => void;
  remindOpen: boolean;
  readOnly: boolean;
}) {
  const shares = barShares(data.totals);
  // Fills, not text: the bar and its keys are drawn as SVG in the theme's colours.
  const parts = [
    { key: "registered", share: shares.registered, fill: "var(--color-lager)", label: copy.registered, count: data.totals.registered },
    { key: "manual", share: shares.manual, fill: "var(--color-ink)", label: copy.manual, count: data.totals.registered_manually },
    {
      key: "unregistered",
      share: shares.unregistered,
      fill: "var(--color-axis)",
      label: copy.unregistered,
      count: data.totals.unregistered,
    },
  ] as const;
  return (
    <div className="max-w-4xl">
      {/* The parts in proportion with a true 2 px gap between neighbours at every width (mockup
          02); a part of zero is left out, so no gap stands for it. */}
      <div aria-hidden="true" className="flex h-8 w-full gap-0.5">
        {parts
          .filter((p) => p.share > 0)
          .map((p) => (
            <svg
              key={p.key}
              viewBox="0 0 1 1"
              preserveAspectRatio="none"
              className="block h-full min-w-0.5 basis-0"
              style={{ flexGrow: p.share }}
            >
              <rect width={1} height={1} fill={p.fill} />
            </svg>
          ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-6 gap-y-1">
        <ul className="flex flex-wrap gap-x-6 gap-y-1">
          {parts.map((p) => (
            <li key={p.key} className="flex items-center gap-2 text-label text-ink">
              <svg aria-hidden="true" viewBox="0 0 12 12" className="size-3 shrink-0">
                <rect width={12} height={12} fill={p.fill} />
              </svg>
              <span className="tabular-nums">{copy.total(p.label, p.count)}</span>
            </li>
          ))}
        </ul>
        {/* Not when every address waiting is a hard bounce: no reminder could go out, and each
            row already says «Kom ikke fram, permanent feil». */}
        {!readOnly && data.reminder_count > 0 && reminderReach(data.items).reach > 0 ? (
          <button
            type="button"
            className={LINK_BUTTON}
            aria-expanded={remindOpen}
            onClick={(event) => onRemindAll(event.currentTarget)}
          >
            {copy.remindAll(data.reminder_count)}
          </button>
        ) : null}
      </div>
    </div>
  );
}

/** The in-place confirmation: what happens, «Gyldig i antall dager» prefilled with 14, the
 * primary button with its count, and «Avbryt». Focus moves to the field when it opens. */
function Confirm({
  target,
  items,
  sending,
  error,
  onEdit,
  onCancel,
  onSend,
}: {
  target: Target;
  items: readonly Registration[];
  sending: boolean;
  error: string | undefined;
  onEdit: () => void;
  onCancel: () => void;
  onSend: (days: number) => void;
}) {
  const [days, setDays] = useState(String(VALID_DAYS.default));
  const [refused, setRefused] = useState(false);
  const field = useRef<HTMLInputElement>(null);
  useEffect(() => field.current?.focus(), []);
  const all = target.kind === "all";
  const { reach, leftOut } = all ? reminderReach(items) : { reach: 1, leftOut: 0 };
  const id = all ? "reminder-all" : `reminder-${target.item.id}`;
  return (
    <form
      noValidate
      aria-labelledby={`${id}-title`}
      className="flex max-w-md flex-col items-start gap-4 rounded-sm border border-axis px-4 py-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (sending || reach === 0) return;
        const parsed = parseValidDays(days);
        if (parsed === null) {
          setRefused(true);
          return;
        }
        onSend(parsed);
      }}
    >
      <h3 id={`${id}-title`} className="text-label text-ink [overflow-wrap:anywhere]">
        {all ? copy.confirmTitle : isFirst(target.item) ? copy.inviteFor(target.item.email) : copy.resendFor(target.item.email)}
      </h3>
      {all ? <p className="text-body-phone text-ink-secondary">{copy.confirmLead}</p> : null}
      {leftOut > 0 ? <p className="text-body-phone text-ink">{copy.confirmLeft(leftOut)}</p> : null}
      <TextField
        id={`${id}-days`}
        ref={field}
        label={nb.classes.roster.validDays}
        inputMode="numeric"
        autoComplete="off"
        value={days}
        onChange={(event) => {
          setDays(event.target.value);
          setRefused(false);
          onEdit();
        }}
        hint={nb.classes.roster.validDaysHint(VALID_DAYS.min, VALID_DAYS.max)}
        error={refused ? nb.classes.roster.validDaysError(VALID_DAYS.min, VALID_DAYS.max) : undefined}
        className="w-full"
        inputClassName="max-w-[14rem]"
      />
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Button type="submit" variant="primary" unavailable={sending || reach === 0}>
          {sending ? copy.sending : all ? copy.confirm(reach) : isFirst(target.item) ? copy.invite : copy.resend}
        </Button>
        <button type="button" className={LINK_BUTTON} onClick={onCancel}>
          {copy.cancel}
        </button>
      </div>
      <ActionError message={error} />
    </form>
  );
}

/** The result line: how many went out and until when, and the hard bounces left out by name. */
function Result({ outcome, ref }: { outcome: Outcome; ref: Ref<HTMLDivElement> }) {
  const { sent, address, first } = outcome;
  const lastDay = dayLabel(sent.last_valid_day, todayIso());
  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="status"
      className="max-w-2xl text-body-phone text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink lg:text-body"
    >
      <p className="[overflow-wrap:anywhere]">
        {address && sent.sent === 1
          ? (first ? copy.invitedOne : copy.resent)(address, lastDay)
          : copy.sent(sent.sent, lastDay)}
      </p>
      {sent.left_out.length > 0 ? (
        <>
          <p className="mt-2">{copy.leftOut}</p>
          <ul className="mt-1">
            {sent.left_out.map((email) => (
              <li key={email} className="[overflow-wrap:anywhere]">
                {email}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}

/** «Adresser»: the status filter, the address search and one row per address with its status in
 * text and, where a reminder may go, «Send ny Invitasjon». Rows stack at 320 px. */
function AddressList({
  items,
  open,
  panel,
  onResend,
  onManual,
  onRemove,
  onFilter,
  readOnly,
}: {
  items: readonly Registration[];
  open: { id: string; kind: "resend" | "manual" | "remove" } | null;
  panel: ReactNode;
  onResend: (item: Registration, button: HTMLButtonElement) => void;
  onManual: (item: Registration, button: HTMLButtonElement) => void;
  onRemove: (item: Registration, button: HTMLButtonElement) => void;
  onFilter: () => void;
  readOnly: boolean;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [query, setQuery] = useState("");
  const shown = filterRegistrations(items, status, query);
  const today = todayIso();
  return (
    <section aria-labelledby="registration-list-title" className="max-w-4xl">
      <h3 id="registration-list-title" className="text-step-title text-ink">
        {copy.listTitle}
      </h3>
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-4">
        <SelectField
          id="registration-filter"
          label={copy.filter}
          value={status ?? ""}
          onChange={(event) => {
            onFilter();
            setStatus(event.target.value === "" ? null : (event.target.value as Status));
          }}
          className="w-full max-w-xs"
        >
          <option value="">{copy.filterAll}</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {copy.status[s]}
            </option>
          ))}
        </SelectField>
        <TextField
          id="registration-search"
          label={copy.search}
          type="search"
          autoComplete="off"
          value={query}
          onChange={(event) => {
            onFilter();
            setQuery(event.target.value);
          }}
          className="w-full max-w-xs"
        />
      </div>
      <p role="status" className="mt-3 text-body-phone text-ink-secondary">
        {shown.length === 0 ? copy.noMatch : copy.shown(shown.length, items.length)}
      </p>
      <ul className="mt-2 border-t border-hairline">
        {shown.map((item) => (
          <li key={item.id} className="border-b border-hairline py-2">
            <div className="flex flex-col gap-1 sm:grid sm:min-h-tap-target-min sm:grid-cols-[minmax(0,1fr)_minmax(0,12rem)_minmax(0,21rem)] sm:items-center sm:gap-x-4">
              <span className="text-body-phone text-ink [overflow-wrap:anywhere] lg:text-body">{item.email}</span>
              <span className="text-body-phone text-ink-secondary lg:text-body">{statusLabel(item, today)}</span>
              {readOnly ? null : (
              <span className="flex flex-wrap gap-x-4 sm:justify-self-end">
                {item.remindable ? (
                  <button
                    type="button"
                    className={LINK_BUTTON}
                    aria-label={isFirst(item) ? copy.inviteFor(item.email) : copy.resendFor(item.email)}
                    aria-expanded={open?.id === item.id && open.kind === "resend"}
                    onClick={(event) => onResend(item, event.currentTarget)}
                  >
                    {isFirst(item) ? copy.invite : copy.resend}
                  </button>
                ) : null}
                {isRegistered(item) ? null : (
                  <button
                    type="button"
                    className={LINK_BUTTON}
                    aria-label={entries.manualFor(item.email)}
                    aria-expanded={open?.id === item.id && open.kind === "manual"}
                    onClick={(event) => onManual(item, event.currentTarget)}
                  >
                    {entries.manual}
                  </button>
                )}
                <button
                  type="button"
                  className={LINK_BUTTON}
                  aria-label={entries.removeFor(item.email)}
                  aria-expanded={open?.id === item.id && open.kind === "remove"}
                  onClick={(event) => onRemove(item, event.currentTarget)}
                >
                  {entries.remove}
                </button>
              </span>
              )}
            </div>
            {open?.id === item.id ? <div className="mt-2 mb-2">{panel}</div> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Today as an ISO date on the browser's clock, for the year in the day labels. */
function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
