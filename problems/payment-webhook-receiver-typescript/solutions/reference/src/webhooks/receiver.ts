// What the shop answers each delivery. The checks run in the order that keeps them honest: the
// signature over the bytes as they came, the timestamp it covers, the event, its id, and its place
// among the order's events. A 4xx tells the provider never to send it again; a 5xx, to try later.

import { isDeepStrictEqual } from "node:util";

import { parseEvent } from "../events.ts";
import type { PaymentEvent } from "../events.ts";
import type { OrderBook } from "../orders.ts";
import { ProviderUnavailable } from "../provider.ts";
import type { ProviderClient } from "../provider.ts";
import { isSigned, isTimely } from "./signature.ts";
import type { Delivery } from "./signature.ts";

export type Answer = { status: number; body: unknown };
export type ReceiverSettings = { secret: string; now: () => number };

function refused(status: number, error: string): Answer {
  return { status, body: { error } };
}

function accepted(outcome: string): Answer {
  return { status: 200, body: { outcome } };
}

export class WebhookReceiver {
  readonly #settings: ReceiverSettings;
  readonly #orders: OrderBook;
  readonly #provider: ProviderClient;

  constructor(settings: ReceiverSettings, orders: OrderBook, provider: ProviderClient) {
    this.#settings = settings;
    this.#orders = orders;
    this.#provider = provider;
  }

  async receive(delivery: Delivery): Promise<Answer> {
    if (!isSigned(this.#settings.secret, delivery)) {
      return refused(401, "invalid signature");
    }
    if (!isTimely(delivery.timestamp, this.#settings.now())) {
      return refused(401, "timestamp outside tolerance");
    }
    const event = parseEvent(delivery.body.toString("utf8"));
    if (event === null) {
      return refused(400, "invalid event");
    }
    const earlier = this.#orders.processed(event.id);
    if (earlier !== undefined) {
      return isDeepStrictEqual(earlier, event) ? accepted("duplicate") : refused(409, "event id reused");
    }
    return this.#place(event);
  }

  async #place(event: PaymentEvent): Promise<Answer> {
    const next = this.#orders.nextSequence(event.order);
    if (event.sequence < next) {
      return refused(409, "illegal transition");
    }
    if (event.sequence > next) {
      const refusal = await this.#fillGap(event.order, next, event.sequence - 1);
      if (refusal !== null) {
        return refusal;
      }
    }
    const placement = this.#orders.place(event);
    return placement === "illegal" ? refused(409, "illegal transition") : accepted(placement);
  }

  /** Applies the events missing before this one, from the provider; an answer when it cannot. */
  async #fillGap(order: string, first: number, last: number): Promise<Answer | null> {
    let missing: PaymentEvent[];
    try {
      missing = await this.#provider.eventsBetween(order, first, last);
    } catch (error) {
      if (!(error instanceof ProviderUnavailable)) {
        throw error;
      }
      console.error(error.message);
      return refused(503, "provider unavailable");
    }
    for (const event of missing) {
      if (this.#orders.place(event) === "illegal") {
        return refused(409, "illegal transition");
      }
    }
    return null;
  }
}
