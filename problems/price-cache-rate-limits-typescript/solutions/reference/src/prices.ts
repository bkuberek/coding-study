// Cache-aside in front of the pricing engine. A kept price is one key holding the engine's body and
// the moment it stops being fresh; the key's TTL covers its stale time after that as well.

import { lifetimeOf } from "./cacheControl.ts";
import { fetchPrice } from "./pricing.ts";
import { store } from "./store.ts";

export type Lookup =
  | { kind: "price"; body: string; cache: "hit" | "miss" | "stale" }
  | { kind: "unknown" }
  | { kind: "unavailable" };

type Kept = { body: string; freshUntil: number };

const inFlight = new Map<string, Promise<Lookup>>();

function keyOf(sku: string): string {
  return `price:${sku}`;
}

export async function lookUp(sku: string): Promise<Lookup> {
  const text = await store.get(keyOf(sku));
  if (text === null) {
    return fetchOnce(sku);
  }
  const kept = JSON.parse(text) as Kept;
  if (Date.now() < kept.freshUntil) {
    return { kind: "price", body: kept.body, cache: "hit" };
  }
  fetchOnce(sku).catch((error: unknown) => console.error(`refreshing ${sku}:`, error));
  return { kind: "price", body: kept.body, cache: "stale" };
}

export async function forget(sku: string): Promise<void> {
  await store.del(keyOf(sku));
}

// One fetch per SKU at a time: a request that misses while one runs shares its answer.
function fetchOnce(sku: string): Promise<Lookup> {
  let pending = inFlight.get(sku);
  if (pending === undefined) {
    pending = fetchAndKeep(sku).finally(() => inFlight.delete(sku));
    inFlight.set(sku, pending);
  }
  return pending;
}

async function fetchAndKeep(sku: string): Promise<Lookup> {
  let answer;
  try {
    answer = await fetchPrice(sku);
  } catch {
    return { kind: "unavailable" };
  }
  if (answer.status === 404) {
    return { kind: "unknown" };
  }
  if (answer.status !== 200) {
    return { kind: "unavailable" };
  }
  const lifetime = lifetimeOf(answer.cacheControl);
  if (lifetime !== null) {
    const kept: Kept = { body: answer.body, freshUntil: Date.now() + lifetime.freshS * 1000 };
    await store.set(keyOf(sku), JSON.stringify(kept), { EX: lifetime.freshS + lifetime.staleS });
  }
  return { kind: "price", body: answer.body, cache: "miss" };
}
