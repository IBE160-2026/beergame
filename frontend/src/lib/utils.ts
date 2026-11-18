import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

import tokens from "@/theme/tokens.json";

// Teach tailwind-merge the theme's own token names, so that `text-label` (a type role) and
// `text-lager` (a colour) are not treated as conflicting classes.
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      color: Object.keys(tokens.colors),
      text: Object.keys(tokens.typography),
      radius: Object.keys(tokens.rounded),
      spacing: Object.keys(tokens.spacing),
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
