// The provider's signature: an HMAC-SHA256 of the timestamp, a dot and the body's bytes as they came,
// keyed with the shop's secret. Both checks read only what arrived, before anything is parsed.

import { createHmac, timingSafeEqual } from "node:crypto";

export const TOLERANCE_S = 300;
const HEX_DIGEST = /^[0-9a-f]{64}$/;
const WHOLE_SECONDS = /^\d+$/;

export type Delivery = {
  timestamp: string | undefined;
  signature: string | undefined;
  body: Buffer;
};
export type SignedDelivery = Delivery & { timestamp: string; signature: string };

export function expectedSignature(secret: string, timestamp: string, body: Buffer): string {
  return createHmac("sha256", secret).update(`${timestamp}.`).update(body).digest("hex");
}

/**
 * Whether the delivery carries the provider's signature of its own timestamp and body. The format
 * is checked first, so the constant-time compare always meets two digests of the same length.
 */
export function isSigned(secret: string, delivery: Delivery): delivery is SignedDelivery {
  const { timestamp, signature, body } = delivery;
  if (timestamp === undefined || signature === undefined || !HEX_DIGEST.test(signature)) {
    return false;
  }
  const expected = Buffer.from(expectedSignature(secret, timestamp, body), "hex");
  return timingSafeEqual(expected, Buffer.from(signature, "hex"));
}

/** Whether a timestamp is whole seconds, no further than the tolerance from now either way. */
export function isTimely(timestamp: string, now: number): boolean {
  return WHOLE_SECONDS.test(timestamp) && Math.abs(now - Number(timestamp)) <= TOLERANCE_S;
}
