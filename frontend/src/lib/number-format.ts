/**
 * The one Norwegian number formatter (Story 5.3, UX-DR5; Epic 6 reuses and extends it). It
 * takes a number or the api's decimal string («0.50») and writes a no-break space as the
 * thousands separator, a decimal comma and a true minus sign («−1 234,50»). `parseNumber` reads a
 * Norwegian number the way a Lecturer types it back into the api's decimal string. Neither holds
 * a rule about which values are allowed: the api judges those.
 */

export const MINUS = "−";
export const GROUP = " ";

const DECIMAL = /^-?\d+(\.\d+)?$/;

export type NumberFormatOptions = {
  /** Exactly this many decimals, padded or rounded («0.5» → «0,50» with 2). */
  decimals?: number;
};

function fixed(text: string, decimals: number | undefined): string {
  if (decimals === undefined) return text;
  const [whole, fraction = ""] = text.split(".");
  if (fraction.length <= decimals) {
    return decimals === 0 ? whole : `${whole}.${fraction.padEnd(decimals, "0")}`;
  }
  // Half up on the digits themselves, so «0.505» is «0.51» (a float would make it 0.50).
  let digits = whole + fraction.slice(0, decimals);
  if (fraction[decimals] >= "5") {
    const chars = digits.split("");
    let i = chars.length - 1;
    while (i >= 0 && chars[i] === "9") chars[i--] = "0";
    if (i < 0) chars.unshift("1");
    else chars[i] = String(Number(chars[i]) + 1);
    digits = chars.join("");
  }
  const cut = digits.length - decimals;
  return decimals === 0 ? digits : `${digits.slice(0, cut)}.${digits.slice(cut)}`;
}

/** «1 234,50», «−3», «0,50»: a number or decimal string in Norwegian. Text that is no number is
 * returned as it is. */
export function formatNumber(value: number | string, options: NumberFormatOptions = {}): string {
  const text = typeof value === "number" ? (Number.isFinite(value) ? String(value) : "") : value.trim();
  if (!DECIMAL.test(text)) return typeof value === "number" ? String(value) : value;
  const negative = text.startsWith("-");
  const [whole, fraction] = fixed(negative ? text.slice(1) : text, options.decimals).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, GROUP);
  const sign = negative && /[1-9]/.test(whole + (fraction ?? "")) ? MINUS : "";
  return `${sign}${grouped}${fraction !== undefined ? `,${fraction}` : ""}`;
}

/** The api's decimal string of a number typed the Norwegian way («1 000,5» → «1000.5», «−2» →
 * «-2»); spaces, a decimal comma or point and any minus sign are read. Null for anything else,
 * which the caller sends as typed so the api names what is wrong. */
export function parseNumber(text: string): string | null {
  const plain = text
    .trim()
    .replace(/[\s  ]/g, "")
    .replace(/^[−–]/, "-")
    .replace(",", ".");
  if (!DECIMAL.test(plain)) return null;
  const negative = plain.startsWith("-");
  const [whole, fraction] = (negative ? plain.slice(1) : plain).split(".");
  const trimmed = whole.replace(/^0+(?=\d)/, "");
  return `${negative ? "-" : ""}${trimmed}${fraction !== undefined ? `.${fraction}` : ""}`;
}
