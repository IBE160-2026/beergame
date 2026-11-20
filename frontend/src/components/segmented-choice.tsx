import { cn } from "@/lib/utils";

export type SegmentedOption<T extends string> = {
  value: T;
  label: string;
  /** The option cannot be chosen now: it renders `aria-disabled`, in the shared disabled look, and
   * a press leaves the choice as it is. Name the reason with `describedBy` and show it beside. */
  unavailable?: boolean;
  /** The id of text that describes this option (its reason when unavailable). */
  describedBy?: string;
};

/**
 * Valgknapper (DESIGN.md → Components → `segmented-choice`): one segment per option. The active
 * segment is filled `ink` with `paper` text; the others have an `ink-muted` border; an unavailable
 * one has the shared disabled look (`future-tint`, `ink-muted`). Under the segments are native
 * radio buttons in a `fieldset`, so the legend names the group, the arrow keys move the choice and
 * a screen reader reads «1 av 2». Each radio covers its whole segment (transparent), so the tap
 * target is the segment (44 px at least); the focus ring is drawn on the segment. An unavailable
 * option keeps its focus (UX-DR8) but never becomes the choice.
 */
export function SegmentedChoice<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
  describedBy,
  className,
}: {
  name: string;
  legend: string;
  options: readonly SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** The id of help text for the whole group, such as its scope. */
  describedBy?: string;
  className?: string;
}) {
  return (
    <fieldset className={cn("m-0 min-w-0 border-0 p-0", className)} aria-describedby={describedBy}>
      <legend className="mb-field-gap text-label text-ink">{legend}</legend>
      <div className="flex flex-wrap">
        {options.map((option, i) => (
          <label
            key={option.value}
            className={cn(
              "relative -ml-px inline-flex min-h-control-height-phone min-w-tap-target-min flex-auto cursor-pointer items-center justify-center border border-ink-muted bg-paper px-5 py-2 text-button text-ink first:ml-0 hover:z-10 hover:border-ink not-has-checked:active:bg-hairline",
              "has-checked:z-10 has-checked:border-ink has-checked:bg-ink has-checked:text-paper",
              "has-focus-visible:z-20 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink",
              option.unavailable &&
                "cursor-not-allowed border-axis bg-future-tint text-ink-muted hover:border-axis active:bg-future-tint",
              i === 0 && "rounded-l-sm",
              i === options.length - 1 && "rounded-r-sm",
            )}
          >
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              aria-disabled={option.unavailable ? true : undefined}
              aria-describedby={option.describedBy}
              onChange={() => {
                if (!option.unavailable) onChange(option.value);
              }}
              className={cn(
                "absolute inset-0 m-0 cursor-pointer appearance-none opacity-0 focus-visible:outline-none",
                option.unavailable && "cursor-not-allowed",
              )}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
