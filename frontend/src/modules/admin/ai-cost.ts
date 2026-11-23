import { nb } from "@/copy/nb";
import { formatNumber, parseNumber } from "@/lib/number-format";

/**
 * «KI-kostnad per Klasseøkt» (Story 15.6, FR-69, C-3): the amounts the api sums unrounded in
 * USD, written with the shared formatter, and the limit the Admin types.
 */

const copy = nb.admin.aiCost;

/** «12,50 USD» from one USD up; «0,0123 USD» below it, so a cost per Game or per Student of a
 * few cents stays readable against the 0,10 and 0,50 USD targets. */
export function costText(amount: string): string {
  const decimals = Math.abs(Number(amount)) >= 1 ? 2 : 4;
  return copy.configs.usd(formatNumber(amount, { decimals }));
}

/** The limit as typed («12,50», «20») as the api's decimal string; null for anything else, a
 * negative amount or more than eight decimals. */
export function parseLimit(text: string): string | null {
  const parsed = parseNumber(text);
  // The budget column's bounds: at most ten whole digits and eight decimals, never below zero.
  if (parsed === null || !/^\d{1,10}(\.\d{1,8})?$/.test(parsed)) return null;
  return parsed;
}

/** A Game's line: «Spill 2», a Game outside the Class games, or the calls that name none. */
export function gameName(line: { game_id: string | null; number: number | null }): string {
  if (line.game_id === null) return copy.cost.games.noGame;
  return line.number === null ? copy.cost.games.otherGame : copy.cost.games.game(line.number);
}

/** A bar's width against the largest value shown, as a share of 100 %. */
export function costPercent(amount: string, top: number): string {
  const value = Number(amount);
  if (!(top > 0) || !(value > 0)) return "0%";
  return `${Math.min(100, (value / top) * 100)}%`;
}
