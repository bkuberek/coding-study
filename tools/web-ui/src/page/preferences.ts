/** Rules over the stored preferences (docs/specs/web-ui.md#preferences). */

import type { Preferences } from "./types.ts";

/**
 * Whether the editor completes and shows signature help. `autocomplete` is stored as set, so it
 * can be true while code intelligence is off; it applies only while both are on (ADR 0018).
 */
export function autocompleteApplies(preferences: Pick<Preferences, "code_intelligence" | "autocomplete">): boolean {
  return preferences.code_intelligence && preferences.autocomplete;
}
