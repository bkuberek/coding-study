// Each order's payment, as the provider's events have described it so far. Kept in memory: the shop
// has no database here.

import type { PaymentEvent } from "./events.ts";

export type OrderView = { order: string; state: string; sequence: number };

const STATE_AFTER: Readonly<Record<string, string>> = {
  "payment.succeeded": "succeeded",
  "payment.failed": "failed",
  "payment.refunded": "refunded",
  "payment.disputed": "disputed",
};

export class OrderBook {
  readonly #orders = new Map<string, OrderView>();

  apply(event: PaymentEvent): void {
    const state = STATE_AFTER[event.type];
    this.#orders.set(event.order, { order: event.order, state, sequence: event.sequence });
  }

  view(order: string): OrderView | undefined {
    return this.#orders.get(order);
  }
}
