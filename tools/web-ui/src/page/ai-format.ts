/** How the page writes what the AI preview counts and sends, in the words of `cstudy ai`
 * (docs/specs/ai.md#usage-and-the-daily-token-cap). */

import type { AiPurpose, AiUsageCounters } from "./types.ts";

const KIB = 1024;
const COST_DECIMALS = 6;
const MIN_COST_DECIMALS = 2;

/** `12,400`. */
export function count(value: number): string {
  return value.toLocaleString("en-US");
}

/** `$0.00003`: up to six decimals, at least two. */
export function dollars(amount: number): string {
  const digits = amount.toFixed(COST_DECIMALS).replace(/0+$/, "");
  const [whole = "0", fraction = ""] = digits.split(".");
  return `$${whole}.${fraction.padEnd(MIN_COST_DECIMALS, "0")}`;
}

export function requests(value: number): string {
  return value === 1 ? "1 request" : `${count(value)} requests`;
}

/** `cost unknown`, or `$0.00003 known` with the requests whose provider reported none. */
export function costText(counters: Pick<AiUsageCounters, "cost_usd" | "requests_without_cost">): string {
  if (counters.cost_usd === null) return "cost unknown";
  const known = `${dollars(counters.cost_usd)} known`;
  return counters.requests_without_cost > 0 ? `${known}, ${requests(counters.requests_without_cost)} without a reported cost` : known;
}

/** What a purpose is called in a sentence: the consent question, a consent's line. */
export function purposeName(purpose: AiPurpose): string {
  return purpose === "review" ? "AI review" : "the check";
}

/** `812 B`, `2.1 KB`; empty for an item with no size. */
export function sizeText(bytes: number | null): string {
  if (bytes === null) return "";
  return bytes < KIB ? `${bytes} B` : `${(bytes / KIB).toFixed(1)} KB`;
}

/** `16 Nov 2026`, in the reader's time zone, from an instant or a day. */
export function dayText(instant: string): string {
  const day = /^\d{4}-\d{2}-\d{2}$/.test(instant) ? new Date(`${instant}T12:00:00`) : new Date(instant);
  if (Number.isNaN(day.getTime())) return instant;
  const month = day.toLocaleDateString("en-US", { month: "short" });
  return `${day.getDate()} ${month} ${day.getFullYear()}`;
}
