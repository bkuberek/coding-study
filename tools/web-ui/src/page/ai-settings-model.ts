/**
 * What the Settings view's AI section says (docs/specs/web-ui.md#settings-view): a provider's key,
 * the consents, today's usage and the last days', and why Check and Load models wait, in the
 * words of `cstudy ai`.
 */

import { costText, count, dayText, requests } from "./ai-format.ts";
import { listed } from "./removal-model.ts";
import type { AiConsent, AiProvider, AiPurpose, AiToday, AiUsage, AiUsageRow } from "./types.ts";

export const PROVIDERS: readonly AiProvider[] = ["anthropic", "google", "openai", "openrouter"];

/** The first part of every key the AI section draws from `config.toml`. */
const AI_KEYS = "ai.";

/** What a provider's key row says of the key: what is saved, then what Save would do. */
export function keyState(set: boolean, staged: "key" | "removal" | null): string {
  const saved = set ? "key set" : "no key";
  if (staged === "key") return `${saved} · new key staged`;
  return staged === "removal" ? `${saved} · removal staged` : saved;
}

/** What a Save of the keys did, as `credentials.toml saved: a key for anthropic` reads. */
export function keysSaved(set: readonly string[], removed: readonly string[]): string {
  const parts = [...(set.length > 0 ? [`a key for ${listed(set)}`] : []), ...(removed.length > 0 ? [`removed the key for ${listed(removed)}`] : [])];
  return `saved: ${parts.join(" · ")}`;
}

/** Why a provider's key was not written, naming the provider, with what an earlier one did. The
 * message is the server's, which never holds a key. */
export function keysRefused(provider: string, message: string, set: readonly string[], removed: readonly string[]): string {
  const before = set.length + removed.length > 0 ? ` (${keysSaved(set, removed)})` : "";
  return `${provider}: ${message}${before}`;
}

/** The purpose as a consent's line names it. */
export function purposeLabel(purpose: AiPurpose): string {
  return purpose === "review" ? "AI review" : "check";
}

/** `anthropic:<model id> · AI review · since 16 Nov 2026`. */
export function consentLine(consent: AiConsent): string {
  return `${consent.provider}:${consent.model} · ${purposeLabel(consent.purpose)} · since ${dayText(consent.granted_at)}`;
}

/** `12,400 of 500,000 tokens · 3 requests · $0.00003 known`. */
export function todayLine(today: AiToday): string {
  const parts = [`${count(today.tokens)} of ${count(today.cap)} tokens`, requests(today.requests)];
  return (today.requests > 0 ? [...parts, costText(today)] : parts).join(" · ");
}

/** One row of the last days' table, by day, provider and model. */
export function usageCells(row: AiUsageRow): readonly string[] {
  return [dayText(row.day), `${row.provider}:${row.model}`, purposeLabel(row.purpose), requests(row.requests), count(row.counted_tokens), costText(row)];
}

/** The table's last row, which adds the rows up. */
export function usageTotal({ total }: AiUsage): readonly string[] {
  return ["total", "", "", requests(total.requests), count(total.counted_tokens), costText(total)];
}

export const USAGE_HEADS: readonly string[] = ["day", "model", "for", "requests", "tokens", "cost"];

/** Why Check and Load models are disabled, or null when they are not: they use what is saved, so
 * they wait while AI is off and while a change of the AI section is staged. */
export function actionsReason(enabled: boolean | null, staged: boolean): string | null {
  if (enabled === null) return "Reading the AI status…";
  if (!enabled) return "AI is off: turn it on and save to use Check and Load models.";
  return staged ? "Save your AI changes first: Check and Load models use what is saved." : null;
}

/** Whether a change of `config.toml` is a key of the AI section. */
export function aiChanges(changes: Readonly<Record<string, unknown>>): boolean {
  return Object.keys(changes).some((name) => name.startsWith(AI_KEYS));
}

/** The values `ai.model`, `ai.fast` and `ai.strong` take for the ids a provider listed, one per
 * line of `cstudy ai models`, sorted; the lines are text, so a line that holds a space is not an id. */
export function modelValues(provider: string, lines: readonly string[]): readonly string[] {
  const ids = lines.map((line) => line.trim()).filter((line) => line !== "" && !/\s/.test(line));
  return [...new Set(ids)].map((id) => `${provider}:${id}`);
}
