// JSON output with a stable shape, so two equal values always serialize to the same text.

/** Like `JSON.stringify`, with the keys of every object in sorted order. */
export function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_key, item: unknown) => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      return item;
    }
    return Object.fromEntries(
      Object.entries(item).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)),
    );
  });
}
