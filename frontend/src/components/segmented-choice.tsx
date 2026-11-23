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
 * option keeps its focus (UX-DR8) but never becomes the choice. Four options stand 2 + 2 on a
 * phone, never 3 + 1. Five (a scale of steps 0 to 4) stand in one row of equal segments from
 * `sm` on, and one under the other on a phone, never 4 + 1. Segments that wrap onto a new line (long labels on a phone) keep a gap
 * between the lines instead of touching.
 */
export function SegmentedChoice<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
  describedBy,
  className,
  inline = false,
}: {
  name: string;
  legend: string;
  options: readonly SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** The id of help text for the whole group, such as its scope. */
  describedBy?: string;
  className?: string;
  /** The legend stands left of the segments, each segment as wide as its text: a compact
   * control beside a chart (the Oversikt's «Visning», `08-laerer-oversikt.png`). */
  inline?: boolean;
}) {
  const quad = options.length === 4;
  const five = !inline && options.length === 5;
  return (
    <fieldset className={cn("m-0 min-w-0 border-0 p-0", inline && "flex-none", className)} aria-describedby={describedBy}>
      <legend
        className={cn(
          "text-label text-ink",
          inline ? "float-left mr-3 flex min-h-control-height-phone items-center text-caption text-ink-secondary" : "mb-field-gap",
        )}
      >
        {legend}
      </legend>
      <div className={cn(inline ? "inline-flex" : "flex flex-wrap gap-y-2", quad && "max-sm:grid max-sm:grid-cols-2 max-sm:gap-y-0", five && "max-sm:flex-col max-sm:gap-y-0 sm:grid sm:grid-cols-5")}>
        {options.map((option, i) => (
          <label
            key={option.value}
            className={cn(
              "relative -ml-px inline-flex min-w-tap-target-min cursor-pointer items-center justify-center border border-ink-muted bg-paper px-5 py-2 text-button text-ink first:ml-0 hover:z-10 hover:border-ink not-has-checked:active:bg-hairline",
              "min-h-control-height-phone", inline ? "flex-none px-4 py-1" : "flex-auto",
              "has-checked:z-10 has-checked:border-ink has-checked:bg-ink has-checked:text-paper",
              "has-focus-visible:z-20 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ink",
              option.unavailable &&
                "cursor-not-allowed border-axis bg-future-tint text-ink-muted hover:border-axis active:bg-future-tint",
              i === 0 && "rounded-l-sm",
              i === options.length - 1 && "rounded-r-sm",
              // 2 + 2: the second row overlaps the first by its border, and each corner is rounded.
              quad && i === 0 && "max-sm:rounded-bl-none",
              quad && i === 1 && "max-sm:rounded-tr-sm",
              quad && i === 2 && "max-sm:-mt-px max-sm:ml-0 max-sm:rounded-bl-sm",
              quad && i === 3 && "max-sm:-mt-px max-sm:rounded-tr-none",
              // One under the other on a phone: each overlaps the one above by its border.
              five && i > 0 && "max-sm:-mt-px max-sm:ml-0",
              five && i === 0 && "max-sm:rounded-tr-sm max-sm:rounded-bl-none",
              five && i === 4 && "max-sm:rounded-tr-none max-sm:rounded-bl-sm",
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
