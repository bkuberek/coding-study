// Plays the payment provider from a test: signs a body the way it does and delivers it to your app,
// and sets a visible scenario on its events API. The secret and the frozen clock come from your app's
// environment, and `cstudy test` gives your tests the address and token of the scenarios.

import { createHmac } from "node:crypto";

const app = `http://127.0.0.1:${process.env.PORT}`;
const control = process.env.CSTUDY_MOCK_CONTROL_URL;
const authorization = { Authorization: `Bearer ${process.env.CSTUDY_MOCK_CONTROL_TOKEN}` };

/** The sandbox's now, in whole seconds since the Unix epoch. */
export const NOW = Number(process.env.CLOCK_NOW);

/** The provider's signature of a body at a timestamp, with the shop's secret. */
export function sign(body: string, timestamp: number | string): string {
  return createHmac("sha256", String(process.env.WEBHOOK_SECRET))
    .update(`${timestamp}.${body}`)
    .digest("hex");
}

export type DeliveryOptions = { timestamp?: number | string; signature?: string };

/** Sends a body to your app's webhook as the provider would, signed unless `signature` says otherwise. */
export async function deliver(body: string, options: DeliveryOptions = {}): Promise<Response> {
  const timestamp = options.timestamp ?? NOW;
  return fetch(`${app}/webhooks/payments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Provider-Timestamp": String(timestamp),
      "Provider-Signature": options.signature ?? sign(body, timestamp),
    },
    body,
  });
}

/** What your app says about an order. */
export async function orderView(order: string): Promise<Response> {
  return fetch(`${app}/orders/${order}`);
}

export async function setScenario(scenario: string | null): Promise<void> {
  const response = await fetch(`${control}/mocks/payment-provider/scenario`, {
    method: "PUT",
    headers: { ...authorization, "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!response.ok) {
    throw new Error(`cannot set ${scenario} on payment-provider: ${await response.text()}`);
  }
}

export async function resetProvider(): Promise<void> {
  await fetch(`${control}/reset`, { method: "POST", headers: authorization });
}
