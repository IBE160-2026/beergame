import type { InputHTMLAttributes, Ref } from "react";

import { cn } from "@/lib/utils";

/**
 * Tekstfelt (DESIGN.md → Components → Controls). The label sits above the field. In the invalid
 * state the field has a `restordre` border, and the reason sits directly under the field. The
 * reason is tied to the field by `aria-describedby`, so it is read when the field takes focus.
 * Colour is never the only cue. A `hint` (a rule the value must meet) sits under the field in
 * `ink-secondary` and is read with it too. `notes` (a warning that never blocks) sit under it all
 * in `ink`, each its own line, read with the field; their words carry them, not a colour.
 */
export type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  notes?: readonly string[];
  /** Classes for the input alone, e.g. a narrow field whose hint and error keep the full width. */
  inputClassName?: string;
  ref?: Ref<HTMLInputElement>;
};

export function TextField({ id, label, error, hint, notes = [], className, inputClassName, ...props }: TextFieldProps) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const noteIds = notes.map((_, index) => `${id}-note-${index}`);
  const describedBy = [hint ? hintId : "", error ? errorId : "", ...noteIds].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("flex flex-col gap-field-gap", className)}>
      <label htmlFor={id} className="text-label text-ink">
        {label}
      </label>
      <input
        {...props}
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "min-h-control-height-phone w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre read-only:bg-future-tint read-only:text-ink-muted",
          inputClassName,
        )}
      />
      {hint ? (
        <p id={hintId} className="text-body-phone text-ink-secondary">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-body-phone text-restordre">
          {error}
        </p>
      ) : null}
      {notes.map((note, index) => (
        <p key={noteIds[index]} id={noteIds[index]} className="text-body-phone text-ink">
          {note}
        </p>
      ))}
    </div>
  );
}
