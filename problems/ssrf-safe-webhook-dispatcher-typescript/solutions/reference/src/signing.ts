// The signature a customer checks to know a delivery came from you, unchanged.

import { createHmac } from "node:crypto";

export const SIGNATURE_HEADER = "X-Webhook-Signature";

/** HMAC-SHA256 of the exact body sent, keyed with the endpoint's secret, in hex. */
export function signature(secret: string, body: string): string {
  return `sha256=${createHmac("sha256", secret).update(body).digest("hex")}`;
}
