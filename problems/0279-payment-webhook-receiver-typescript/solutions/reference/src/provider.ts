// The provider's events API, asked only to fill a gap: the events of an order that are missing
// before the one in hand. One request, within a second, and any doubt about its answer is a failure.

import { eventFrom } from "./events.ts";
import type { PaymentEvent } from "./events.ts";

const REQUEST_LIMIT_MS = 1000;

export class ProviderUnavailable extends Error {}

export class ProviderClient {
  readonly #url: string;

  constructor(url: string) {
    this.#url = url;
  }

  /** The order's events numbered `first` to `last`, in order; ProviderUnavailable when it cannot say. */
  async eventsBetween(order: string, first: number, last: number): Promise<PaymentEvent[]> {
    const listed = await this.#orderEvents(order);
    const wanted: PaymentEvent[] = [];
    for (let sequence = first; sequence <= last; sequence += 1) {
      const event = listed.find((candidate) => candidate.sequence === sequence);
      if (event === undefined) {
        throw new ProviderUnavailable(`the provider has no event ${sequence} for ${order} yet`);
      }
      wanted.push(event);
    }
    return wanted;
  }

  async #orderEvents(order: string): Promise<PaymentEvent[]> {
    let body: unknown;
    try {
      const response = await fetch(`${this.#url}/v1/orders/${encodeURIComponent(order)}/events`, {
        signal: AbortSignal.timeout(REQUEST_LIMIT_MS),
      });
      if (!response.ok) {
        throw new Error(`it answered ${response.status}`);
      }
      body = await response.json();
    } catch (error) {
      throw new ProviderUnavailable(`no events for ${order}: ${String(error)}`);
    }
    const listed = typeof body === "object" && body !== null ? Reflect.get(body, "events") : null;
    if (!Array.isArray(listed)) {
      throw new ProviderUnavailable(`the provider's answer for ${order} holds no events`);
    }
    return listed
      .map(eventFrom)
      .filter((event): event is PaymentEvent => event !== null && event.order === order);
  }
}
