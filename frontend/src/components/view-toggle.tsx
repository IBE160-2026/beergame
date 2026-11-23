import { type SegmentedOption, SegmentedChoice } from "./segmented-choice";

/**
 * Visningsbryter (DESIGN.md → Components → `view-toggle`): two segments that switch between two
 * views of the same content, such as a diagram and its list («Vis i plenum», Story 14.6, adds a
 * third: the per-Role Orders charts). Styled as Valgknapper (active `ink`
 * with `paper` text, inactive with an `ink-muted` border) with the same native radios, keyboard
 * operation, focus ring and 44 px targets; the legend names what is being viewed. A view changes
 * nothing stored.
 */
export function ViewToggle<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
  className,
  inline,
}: {
  name: string;
  legend: string;
  options: readonly [SegmentedOption<T>, SegmentedOption<T>] | readonly [SegmentedOption<T>, SegmentedOption<T>, SegmentedOption<T>];
  value: T;
  onChange: (value: T) => void;
  className?: string;
  /** Legend beside the segments, each as wide as its text (`SegmentedChoice`). */
  inline?: boolean;
}) {
  return (
    <SegmentedChoice
      name={name}
      legend={legend}
      options={options}
      value={value}
      onChange={onChange}
      className={className}
      inline={inline}
    />
  );
}
