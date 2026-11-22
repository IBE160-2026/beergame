import { nb } from "@/copy/nb";
import { ApiRequestError } from "@/lib/api/client";
import { formatNumber } from "@/lib/number-format";

const copy = nb.admin.aiCost;

/** The api's limit (`ops/ai_schemas.py`). */
export const FREEZE_SESSIONS_MAX = 50;

/** A share from 0 to 1 as the api stores it («0.0125») in percent («1,25 %»), by moving the
 * decimal point in the text, so no figure is computed a second way (AD-6). */
export function percentText(share: string): string {
  const match = /^(\d+)(?:\.(\d+))?$/.exec(share.trim());
  if (!match) return share;
  const fraction = (match[2] ?? "").padEnd(2, "0");
  const whole = `${match[1]}${fraction.slice(0, 2)}`.replace(/^0+(?=\d)/, "");
  const rest = fraction.slice(2);
  return copy.configs.percent(formatNumber(rest ? `${whole}.${rest}` : whole, { narrow: true }));
}

/** «0,0725 USD» for the api's decimal string. */
export function usdText(amount: string): string {
  return copy.configs.usd(formatNumber(amount));
}

/** The level's Norwegian label, else its name. */
export function levelName(level: { name: string; label?: string | null }): string {
  return level.label ?? level.name;
}

/** «gpt-x · v1»: how the page names a model config. */
export function modelName(config: { name: string; model_version: string }): string {
  return `${config.name} · ${config.model_version}`;
}

/** The line for a refused pin, freeze or lift: the reason for a known code, else `fallback`. */
export function refusalText(error: unknown, reasons: Record<string, string>, fallback: string): string {
  if (error instanceof ApiRequestError && Object.hasOwn(reasons, error.code)) return reasons[error.code];
  return fallback;
}
