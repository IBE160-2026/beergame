import { nb } from "@/copy/nb";
import { formatNumber } from "@/lib/number-format";
import { ADMIN_AI_COST_PATH } from "@/modules/identity/homes";

import { formatDate } from "./invitations";

/**
 * The day of «KI-kostnad per dag» (Story 15.7, FR-69): the api's Europe/Oslo day as «2026-11-19»,
 * the link to it, the days next to it and the amounts in USD with two decimals.
 */

const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

/** The `?dag=` value when it names a real calendar day, else undefined (the page shows today). */
export function parseDay(value: string | null | undefined): string | undefined {
  const match = DAY.exec(value ?? "");
  if (!match) return undefined;
  const [year, month, day] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
    ? match[0]
    : undefined;
}

/** The calendar day `days` after `day` (before it when negative). */
export function shiftDay(day: string, days: number): string {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, date + days)).toISOString().slice(0, 10);
}

/** «19. nov. 2026». Noon UTC is the same calendar day in Oslo. */
export function dayText(day: string): string {
  return formatDate(`${day}T12:00:00Z`);
}

/** «KI-kostnad» for one day, the alert's link (Story 15.7). */
export function dailySpendPath(day: string): string {
  return `${ADMIN_AI_COST_PATH}?dag=${encodeURIComponent(day)}`;
}

/** «1 234,50 USD»: a day's AI spend with two decimals. */
export function dayUsdText(amount: string): string {
  return nb.admin.aiCost.configs.usd(formatNumber(amount, { decimals: 2 }));
}
