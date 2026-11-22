import type { Ref, TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * A Tekstfelt over several lines (DESIGN.md → Components → Controls), for a value too long for
 * one line, such as a fixed Demand series of 36–52 numbers (GitHub issue 102). Label above,
 * reason and hint under it and read with it, as the Tekstfelt.
 */
export type TextAreaFieldProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> & {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  ref?: Ref<HTMLTextAreaElement>;
};

export function TextAreaField({ id, label, error, hint, className, rows = 3, ...props }: TextAreaFieldProps) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [hint ? hintId : "", error ? errorId : ""].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("flex min-w-0 flex-col gap-field-gap", className)}>
      <label id={`${id}-label`} htmlFor={id} className="text-label text-ink">
        {label}
      </label>
      <textarea
        {...props}
        id={id}
        rows={rows}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className="w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre"
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
