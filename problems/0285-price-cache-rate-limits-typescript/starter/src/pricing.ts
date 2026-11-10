// The pricing engine's client. `PRICING_URL` comes from the sandbox's settings, and the engine's
// contract is in vendors/pricing/API.md.

const engine = process.env.PRICING_URL;
const TIMEOUT_MS = 5000;

export type EngineAnswer = { status: number; body: string; cacheControl: string | null };

// Throws when the engine cannot be reached or takes longer than TIMEOUT_MS.
export async function fetchPrice(sku: string): Promise<EngineAnswer> {
  const response = await fetch(`${engine}/v1/prices/${encodeURIComponent(sku)}`, {
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  return {
    status: response.status,
    body: await response.text(),
    cacheControl: response.headers.get("cache-control"),
  };
}
