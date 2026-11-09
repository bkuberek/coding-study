// Sends one event to many endpoints: signed, within the limits, and each result in its place.

import { deliver } from "./delivery.ts";
import type { DeliveryError } from "./delivery.ts";
import type { Endpoint } from "./endpoints.ts";
import { DELIVERIES_PER_HOST, RATE_WINDOW_MS } from "./limits.ts";
import { SIGNATURE_HEADER, signature } from "./signing.ts";
import { HostQueue, HostRateLimiter } from "./throttles.ts";

export type DeliveryResult = {
  endpoint: string;
  status: "delivered" | "failed" | "skipped";
  response_status: number | null;
  error: DeliveryError | "rate_limited" | "endpoint_disabled" | null;
  signature: string;
};

type Verdict = Omit<DeliveryResult, "endpoint" | "signature">;

export class Dispatcher {
  readonly #rateLimiter = new HostRateLimiter(DELIVERIES_PER_HOST, RATE_WINDOW_MS);
  readonly #queue = new HostQueue();

  /**
   * Delivers `event` to every endpoint at once, but to each host one at a time, in the order the
   * list names them, and answers in that order.
   */
  dispatch(endpoints: readonly Endpoint[], event: object): Promise<DeliveryResult[]> {
    const body = JSON.stringify(event);
    return Promise.all(
      endpoints.map((endpoint) => {
        const host = new URL(endpoint.url).hostname;
        return this.#queue.run(host, () => this.#deliverTo(endpoint, host, body));
      }),
    );
  }

  async #deliverTo(endpoint: Endpoint, host: string, body: string): Promise<DeliveryResult> {
    const signed = signature(endpoint.secret, body);
    const verdict = await this.#verdict(endpoint, host, { body, signed });
    return { endpoint: endpoint.id, ...verdict, signature: signed };
  }

  async #verdict(
    endpoint: Endpoint,
    host: string,
    message: { body: string; signed: string },
  ): Promise<Verdict> {
    if (endpoint.disabled) {
      return { status: "skipped", response_status: null, error: "endpoint_disabled" };
    }
    if (!this.#rateLimiter.tryTake(host)) {
      return { status: "skipped", response_status: null, error: "rate_limited" };
    }
    const outcome = await deliver(new URL(endpoint.url), {
      body: message.body,
      headers: { "Content-Type": "application/json", [SIGNATURE_HEADER]: message.signed },
    });
    if (outcome.delivered) {
      endpoint.recordSuccess();
      return { status: "delivered", response_status: outcome.status, error: null };
    }
    endpoint.recordFailure();
    return { status: "failed", response_status: outcome.status, error: outcome.error };
  }
}
