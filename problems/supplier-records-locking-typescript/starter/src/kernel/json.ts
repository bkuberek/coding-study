// One text for one JSON value, whatever order its keys were built in.

export function canonicalJson(value: unknown): string {
  return JSON.stringify(value, (_key, item: unknown) => {
    if (item === null || typeof item !== "object" || Array.isArray(item)) {
      return item;
    }
    const keys = Object.keys(item).sort();
    return Object.fromEntries(keys.map((key) => [key, (item as Record<string, unknown>)[key]]));
  });
}
