// What the engine's Cache-Control header allows: how long a price is fresh, and how long after that
// it may still be shown while a new one is fetched.

const DEFAULT_FRESH_S = 30;

export type Lifetime = { freshS: number; staleS: number };

// A price's lifetime, or null when it must not be kept.
export function lifetimeOf(header: string | null): Lifetime | null {
  const directives = new Map<string, string>();
  for (const part of (header ?? "").split(",")) {
    const [name, value = ""] = part.trim().toLowerCase().split("=", 2);
    if (name !== "") {
      directives.set(name, value);
    }
  }
  if (directives.has("no-store")) {
    return null;
  }
  const freshS = seconds(directives.get("max-age")) ?? DEFAULT_FRESH_S;
  if (freshS === 0) {
    return null;
  }
  return { freshS, staleS: seconds(directives.get("stale-while-revalidate")) ?? 0 };
}

function seconds(value: string | undefined): number | undefined {
  return value !== undefined && /^\d+$/.test(value) ? Number(value) : undefined;
}
