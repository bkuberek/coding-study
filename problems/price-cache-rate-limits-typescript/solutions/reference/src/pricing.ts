// The pricing engine's client. `PRICING_URL` comes from the sandbox's settings, and the engine's
// contract is in vendors/pricing/API.md.

const engine = process.env.PRICING_URL;
const TIMEOUT_MS = 5000;

export type EngineAnswer = { status: number; body: string; cacheControl: string | null };

function priceUrl(sku: string): string {
  return `${engine}/v1/prices/${encodeURIComponent(sku)}`;
}

// Throws when the engine cannot be reached or takes longer than TIMEOUT_MS.
export async function fetchPrice(sku: string): Promise<EngineAnswer> {
  const response = await fetch(priceUrl(sku), { signal: AbortSignal.timeout(TIMEOUT_MS) });
  return {
    status: response.status,
    body: await response.text(),
    cacheControl: response.headers.get("cache-control"),
  };
}

// Whether the engine took the new price.
export async function putPrice(sku: string, amountCents: number): Promise<boolean> {
  try {
    const response = await fetch(priceUrl(sku), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount_cents: amountCents }),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    await response.arrayBuffer();
    return response.status === 204;
  } catch {
    return false;
  }
}
