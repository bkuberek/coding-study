/** What the Settings view's bar says of unsaved changes and of a Save (docs/specs/web-ui.md#settings-view). */

/** How one store's part of a Save ended; null when it held no change. */
export type StoreOutcome = { readonly saved: string } | { readonly error: string } | null;

export interface SaveLine {
  readonly text: string;
  readonly failed: boolean;
}

export function changesText(count: number): string {
  return count === 1 ? "1 change" : `${count} changes`;
}

/** One line per store that held a change, so a failure in one says which and the other its result. */
export function saveLines(config: StoreOutcome, preferences: StoreOutcome): readonly SaveLine[] {
  return [lineOf("config.toml", config), lineOf("preferences", preferences)].flat();
}

function lineOf(store: string, outcome: StoreOutcome): readonly SaveLine[] {
  if (outcome === null) return [];
  return "error" in outcome ? [{ text: `${store} not saved: ${outcome.error}`, failed: true }] : [{ text: `${store} ${outcome.saved}`, failed: false }];
}
