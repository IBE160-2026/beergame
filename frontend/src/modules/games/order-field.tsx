"use client";

import { type KeyboardEvent, type ReactNode, useId, useRef, useState } from "react";

import { Button, guardUnavailable } from "@/components/button";
import { nb } from "@/copy/nb";
import { useConnection } from "@/lib/connection";
import { formatNumber } from "@/lib/number-format";
import type { OrderPreview } from "@/lib/preview";
import { cn } from "@/lib/utils";

import type { PlayTurn } from "./api";
import { orderError, parseOrder, stepOrder } from "./order-input";

const copy = nb.games.play.order;

/** The value box: `order-input` at `order-input-height`, the number in `figure-order`. */
const BOX = "mt-2 flex min-h-order-input-height w-full rounded-sm";
const VALUE = "text-center text-figure-order tabular-nums lining-nums";

type Props = {
  week: number;
  turn: PlayTurn;
  /** The Game settings maximum (`seat_state.max_order`). */
  max: number;
  /** The Order of the Uke before, if there was one (the last `history` row). */
  lastOrder?: number;
  /** The typed text, kept by the play screen so the table and the Kjedebånd can preview it. */
  text: string;
  onText: (text: string) => void;
  /** Where a valid typed value lands (`lib/preview.ts`); null while the text is not valid. */
  preview: OrderPreview | null;
  /** The Order is on its way to the api (Story 6.12): Submitting. */
  sending?: boolean;
  /** «Bekreft ordre på x» pressed with a valid x and nothing on its way. */
  onConfirm?: (value: number) => void;
  /** No answer within the order-submit timeout: the app asks the server (Story 6.13). */
  checking?: boolean;
  /** Why the last send did not place the Order, read as an alert (Story 6.13). */
  failure?: string | null;
  /** The last send failed: the button offers to send the same value again. */
  retry?: boolean;
  /** Whom else the game waits for, in words, once the Order is sent: «Jonas (3 min)» (Story
   * 6.14); null when it waits for no one else. */
  waitingFor?: string | null;
  /** Right-aligned on the label's line, in every state: the Lenke «Alle rader og kostnad» on phone
   * (Story 6.16, DESIGN.md → Ordrefelt). */
  aside?: ReactNode;
  /** An in-place form with its own primary is open on the screen (the Pausevalg, Story 8.6): «Bekreft
   * ordre» steps back to secondary, so the screen keeps one primary button (UX-DR8). */
  stepBack?: boolean;
};

/**
 * Ordrefelt (DESIGN.md → Ordrefelt, EXPERIENCE.md → Ordrefelt, UX-DR20, UX-DR62). In a Veiledet
 * uke (Story 6.10) the Order is fixed and placed for the Student: the field shows it read-only on
 * `future-tint` with the reason under it and no button. Otherwise (Story 6.11) the Student types
 * one whole number from 0 to {maks}, or steps with − and +; the play screen previews a valid
 * value in the table and the Kjedebånd. «Bekreft ordre på 24» sends it (Story 6.12): Submitting
 * while it is on its way, then Confirmed, with no undo and no dialog. A send that failed, timed
 * out or meets an offline device says so in words above the button (Story 6.13). Nothing here
 * suggests a number (UX-DR78) or says how many Veiledede uker remain (FR-14).
 */
export function OrderField(props: Props) {
  const { week, turn } = props;
  if (turn.order != null && turn.guided) return <ReadOnly week={week} order={turn.order} aside={props.aside} />;
  if (turn.order != null) return <Confirmed order={turn.order} waitingFor={props.waitingFor ?? null} aside={props.aside} />;
  if (turn.guided) return null;
  // A new Uke starts the field afresh: no reason or announcement carries over.
  return <Editable key={week} {...props} />;
}

/** A Veiledet uke's fixed Order, read-only, with its reason. It is not a text box to the pointer
 * or the caret either (`cursor: default`, no caret, Issue 128). */
function ReadOnly({ week, order, aside }: { week: number; order: number; aside?: ReactNode }) {
  const id = useId();
  return (
    <div className="mt-8 mb-8 max-w-md lg:mt-0" data-order-field="guided">
      <LabelLine aside={aside}>
        <label htmlFor={`${id}-input`} className="block text-label text-ink">
          {copy.label(week)}
        </label>
      </LabelLine>
      <input
        id={`${id}-input`}
        type="text"
        inputMode="numeric"
        readOnly
        aria-describedby={`${id}-guided`}
        value={String(order)}
        className={cn(BOX, VALUE, "block cursor-default caret-transparent border border-ink-muted bg-future-tint px-3 text-ink-muted")}
      />
      <p id={`${id}-guided`} className="mt-2 text-caption text-ink-secondary">
        {copy.guided}
      </p>
    </div>
  );
}

/** Confirmed (Story 6.12, EXPERIENCE.md → State Patterns → Spill, `06-spilldynamikk.png` C): the
 * Order is sent and cannot change. «Ordren på 24 er sendt.» is where the play screen puts focus
 * right after the send (`tabindex="-1"`, `data-order-sent`, read on focus), with what happens
 * next under it. The table and the Kjedebånd keep showing the Order. While the game waits for
 * others it names them with the wait: «Ordren på 24 er sendt. Venter på Jonas (3 min).» (Story
 * 6.14, never «Venter på andre spillere …»). */
function Confirmed({ order, waitingFor, aside }: { order: number; waitingFor: string | null; aside?: ReactNode }) {
  const value = formatNumber(order);
  return (
    <div className="mt-8 mb-8 max-w-md lg:mt-0" data-order-field="confirmed">
      {aside ? <div className="flex justify-end">{aside}</div> : null}
      <p data-order-sent="" tabIndex={-1} className="text-body-phone font-bold text-ink outline-none lg:text-body">
        {waitingFor ? copy.sentWaiting(value, waitingFor) : copy.sent(value)}
      </p>
      <p className="mt-2 text-caption text-ink-secondary">{copy.next}</p>
    </div>
  );
}

function Editable({
  week,
  max,
  lastOrder,
  text,
  onText,
  preview,
  sending = false,
  onConfirm,
  checking = false,
  failure = null,
  retry = false,
  aside,
  stepBack = false,
}: Props) {
  const id = useId();
  const connection = useConnection();
  const button = useRef<HTMLButtonElement>(null);
  // An empty field shows its reason only once the button was pressed.
  const [pressedEmpty, setPressedEmpty] = useState(false);
  // What `role="alert"` reads: set on leaving the field or pressing the button, never per keystroke.
  const [alert, setAlert] = useState<{ text: string; n: number } | null>(null);
  // What − and + announce politely.
  const [stepped, setStepped] = useState("");

  const parsed = parseOrder(text, max);
  const limit = formatNumber(max);
  const error = orderError(parsed, max) ?? (parsed.kind === "empty" && pressedEmpty ? copy.invalid(limit) : null);
  const valid = parsed.kind === "valid" ? parsed.value : null;

  const change = (next: string) => {
    if (sending) return; // The field is read-only while the Order is on its way.
    onText(next);
    setPressedEmpty(false);
    setAlert(null);
  };
  const announce = (message: string | null) => {
    if (message) setAlert((was) => ({ text: message, n: (was?.n ?? 0) + 1 }));
  };
  const step = (direction: -1 | 1) => {
    if (sending) return;
    const next = stepOrder(parsed, max, direction);
    if (next === null) return;
    change(String(next));
    setStepped(copy.stepped(formatNumber(next)));
  };
  const press = () => {
    if (sending) return; // Further presses are ignored while the Order is on its way.
    if (valid !== null) {
      onConfirm?.(valid);
      return;
    }
    if (parsed.kind === "empty") setPressedEmpty(true);
    announce(error ?? copy.invalid(limit));
  };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    // Enter never sends: it moves to the button, which alone confirms.
    if (event.key !== "Enter") return;
    event.preventDefault();
    button.current?.focus();
  };

  // What the order area says about the send (Story 6.13, UX-DR60), politely: the server is being
  // asked, or the device is offline (or just back) with a typed value that is not sent.
  const unsent = valid !== null && !sending && !failure ? formatNumber(valid) : null;
  const status = checking
    ? copy.checking
    : unsent !== null && connection === "offline"
      ? copy.offline(unsent)
      : unsent !== null && connection === "reconnected"
        ? copy.reconnected
        : null;
  const label =
    valid === null
      ? copy.confirm
      : sending
        ? copy.sending(formatNumber(valid))
        : retry
          ? copy.retry(formatNumber(valid))
          : copy.confirmOn(formatNumber(valid));

  const fewer = sending || stepOrder(parsed, max, -1) === null;
  const more = sending || stepOrder(parsed, max, 1) === null;
  const describedBy = [`${id}-help`, error ? `${id}-error` : null].filter(Boolean).join(" ");
  return (
    <div className="mt-8 mb-8 max-w-md lg:mt-0" data-order-field="editable">
      <LabelLine aside={aside}>
        <label htmlFor={`${id}-input`} className="block text-label text-ink">
          {copy.label(week)}
        </label>
      </LabelLine>
      <div
        data-order-box=""
        className={cn(
          BOX,
          "has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-ink",
          error
            ? "border-[1.4px] border-restordre"
            : valid !== null
              ? "border-[1.4px] border-ink"
              : "border border-ink-muted hover:border-ink",
        )}
      >
        <Segment label={copy.fewer} sign="−" unavailable={fewer} onPress={() => step(-1)} side="left" />
        <input
          id={`${id}-input`}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          autoComplete="off"
          placeholder={copy.placeholder}
          value={text}
          readOnly={sending}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(event) => change(event.target.value)}
          onBlur={() => announce(error)}
          onKeyDown={onKeyDown}
          className={cn(
            VALUE,
            "min-w-0 flex-1 px-2 outline-none placeholder:text-body placeholder:text-ink-muted",
            // Read-only while submitting (DESIGN.md → Ordrefelt): `future-tint` fill, value in `ink-muted`.
            sending ? "bg-future-tint text-ink-muted" : "bg-paper text-ink",
          )}
        />
        <Segment label={copy.more} sign="+" unavailable={more} onPress={() => step(1)} side="right" />
      </div>
      <p id={`${id}-help`} className="mt-2 text-caption text-ink-secondary">
        {copy.help(limit)}
      </p>
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-caption text-restordre">
          {error}
        </p>
      ) : null}
      {parsed.kind === "empty" && lastOrder !== undefined ? (
        <p className="mt-1 text-caption text-ink-secondary">{copy.last(formatNumber(lastOrder))}</p>
      ) : null}
      <div role="alert" className="sr-only">
        {alert ? <span key={alert.n}>{alert.text}</span> : null}
      </div>
      <p aria-live="polite" className="sr-only" data-order-announce="">
        {sending ? (valid !== null && !checking ? copy.sending(formatNumber(valid)) : "") : stepped}
      </p>
      {valid !== null && preview ? (
        <p className="mt-3 text-caption text-ink-secondary" data-order-arrives="">
          {copy.arrives(preview.arrivalWeek)}
        </p>
      ) : null}
      {/* Both regions are always there, so a message that appears is read: a failed send
          assertively, the rest politely. Focus stays on the button. */}
      <div role="alert" data-order-failure="">
        {failure ? <p className="mt-3 text-body-phone font-bold text-ink lg:text-body">{failure}</p> : null}
      </div>
      <div aria-live="polite" data-order-status="">
        {status ? <p className="mt-3 text-body-phone text-ink lg:text-body">{status}</p> : null}
      </div>
      {/* Unavailable until the value is valid, yet a press still says why (`onClickCapture` runs
          before the guard that ignores the press). While sending it keeps focus, busy. */}
      <Button
        ref={button}
        variant={stepBack ? "secondary" : "primary"}
        unavailable={valid === null || sending}
        aria-busy={sending ? true : undefined}
        onClickCapture={press}
        className="mt-3 w-full"
      >
        {label}
      </Button>
    </div>
  );
}

/** The label with `aside` right-aligned on its line, as drawn; the label alone without it. */
function LabelLine({ aside, children }: { aside?: ReactNode; children: ReactNode }) {
  if (!aside) return <>{children}</>;
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4">
      {children}
      {aside}
    </div>
  );
}

/** − or +: an outlined segment inside the box, at least 44 px wide and as tall as the box. One
 * that cannot act keeps focus with `aria-disabled` and ignores presses. */
function Segment({
  label,
  sign,
  unavailable,
  onPress,
  side,
}: {
  label: string;
  sign: string;
  unavailable: boolean;
  onPress: () => void;
  side: "left" | "right";
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-disabled={unavailable ? true : undefined}
      onClick={guardUnavailable(unavailable, onPress)}
      className={cn(
        "flex w-order-input-height shrink-0 cursor-pointer items-center justify-center bg-paper text-title-phone text-ink",
        "hover:not-aria-disabled:bg-hairline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        "aria-disabled:cursor-not-allowed aria-disabled:bg-future-tint aria-disabled:text-ink-muted",
        side === "left" ? "rounded-l-sm border-r border-ink-muted" : "rounded-r-sm border-l border-ink-muted",
      )}
    >
      <span aria-hidden="true">{sign}</span>
    </button>
  );
}
