import type { Ref, SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/**
 * A labelled native select, styled as the Tekstfelt (DESIGN.md → Components → Controls). As the
 * Tekstfelt, the invalid state has a `restordre` border and the reason directly under the field,
 * tied to it by `aria-describedby`; a `hint` sits under it in `ink-secondary`.
 */
export type SelectFieldProps = Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  ref?: Ref<HTMLSelectElement>;
};

export function SelectField({ id, label, error, hint, className, children, ...props }: SelectFieldProps) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [hint ? hintId : "", error ? errorId : ""].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("flex min-w-0 flex-col gap-field-gap", className)}>
      <label htmlFor={id} className="text-label text-ink">
        {label}
      </label>
      <select
        {...props}
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className="min-h-control-height-phone w-full min-w-0 rounded-sm border border-ink-muted bg-paper px-3 py-2 text-button font-normal text-ink hover:border-ink aria-invalid:border-[1.4px] aria-invalid:border-restordre"
      >
        {children}
      </select>
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
