import type { InputHTMLAttributes, Ref } from "react";

import { cn } from "@/lib/utils";

/**
 * Tekstfelt (DESIGN.md → Components → Controls). The label sits above the field. In the invalid
 * state the field has a `restordre` border, and the reason sits directly under the field. The
 * reason is tied to the field by `aria-describedby`, so it is read when the field takes focus.
 * Colour is never the only cue. A `hint` (a rule the value must meet) sits under the field in
 * `ink-secondary` and is read with it too.
 */
export type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  ref?: Ref<HTMLInputElement>;
};

export function TextField({ id, label, error, hint, className, ...props }: TextFieldProps) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [hint ? hintId : "", error ? errorId : ""].filter(Boolean).join(" ") || undefined;
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
        className="min-h-control-height-phone w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre read-only:bg-future-tint read-only:text-ink-muted"
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
    </div>
  );
}
