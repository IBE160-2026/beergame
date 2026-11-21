import tokens from "@/theme/tokens.json";

/**
 * Chart paint from the theme tokens (UX-DR1). Charts write colours as SVG presentation attributes
 * taken from `tokens.json`, not as classes or CSS variables, so an SVG is self-contained: the same
 * markup draws in the browser, in a server render and in WeasyPrint's SVG renderer (AD-18).
 */
export type ColourToken = keyof typeof tokens.colors;

export function colour(name: ColourToken): string {
  return tokens.colors[name];
}

/** The self-hosted text face (AD-18), with the theme's fallbacks. */
export const CHART_FONT = '"Source Sans 3", "Source Sans Pro", "Segoe UI", Arial, sans-serif';
