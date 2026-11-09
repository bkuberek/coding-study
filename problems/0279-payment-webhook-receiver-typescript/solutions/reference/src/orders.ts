// Each order's payment, moved by the provider's events one sequence number at a time, and only along
// the transitions a payment can make. Kept in memory: the shop has no database here.

import type { PaymentEvent } from "./events.ts";

export type State = "pending" | "succeeded" | "failed" | "refunded" | "disputed";
export type OrderView = { order: string; state: State; sequence: number };
export type Placement = "applied" | "ignored" | "illegal";

const STATE_AFTER: Readonly<Record<string, State>> = {
  "payment.succeeded": "succeeded",
  "payment.failed": "failed",
  "payment.refunded": "refunded",
  "payment.disputed": "disputed",
};

const NEXT_STATES: Readonly<Record<State, readonly State[]>> = {
  pending: ["succeeded", "failed"],
  failed: ["failed", "succeeded"],
  succeeded: ["refunded", "disputed"],
  refunded: [],
  disputed: [],
};

/** Whether a payment in one state can move to another. */
export function canMove(from: State, to: State): boolean {
  return NEXT_STATES[from].includes(to);
}

export class OrderBook {
  readonly #orders = new Map<string, OrderView>();
  readonly #processed = new Map<string, PaymentEvent>();

  /** The event already applied under this id, if any. */
  processed(id: string): PaymentEvent | undefined {
    return this.#processed.get(id);
  }

  /** The sequence number the order's next event carries. */
  nextSequence(order: string): number {
    return (this.#orders.get(order)?.sequence ?? 0) + 1;
  }

  /**
   * Applies an event that carries its order's next sequence number. A type this service does not
   * handle moves nothing but still takes its place; one the machine does not allow changes nothing.
   */
  place(event: PaymentEvent): Placement {
    const current = this.#orders.get(event.order) ?? {
      order: event.order,
      state: "pending",
      sequence: 0,
    };
    const target = Object.hasOwn(STATE_AFTER, event.type) ? STATE_AFTER[event.type] : undefined;
    if (target !== undefined && !canMove(current.state, target)) {
      return "illegal";
    }
    this.#orders.set(event.order, {
      order: event.order,
      state: target ?? current.state,
      sequence: event.sequence,
    });
    this.#processed.set(event.id, event);
    return target === undefined ? "ignored" : "applied";
  }

  view(order: string): OrderView | undefined {
    return this.#orders.get(order);
  }
}
