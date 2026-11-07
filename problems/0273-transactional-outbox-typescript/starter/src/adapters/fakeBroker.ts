// The message broker other services read from, faked. It can refuse a message, and it can take one
// and then fail to say so.

import { PublishFailed } from "../core/ports.ts";
import type { BrokerEvent } from "../core/ports.ts";

type Listener = (event: BrokerEvent) => void;

export class FakeBroker {
  readonly #log: BrokerEvent[] = [];
  readonly #listeners: Listener[] = [];
  readonly #refusals = new Map<string, number>();
  readonly #lostAcks = new Set<string>();

  /** The next `times` messages for this aggregate are refused. */
  refuseNext(aggregateId: string, times: number): void {
    this.#refusals.set(aggregateId, times);
  }

  /** The next message for this aggregate is taken and delivered, and the confirmation is lost. */
  loseNextAck(aggregateId: string): void {
    this.#lostAcks.add(aggregateId);
  }

  /** Called with every message the broker delivers, in the order it delivers them. */
  subscribe(listener: Listener): void {
    this.#listeners.push(listener);
  }

  publish(event: BrokerEvent): void {
    const refusals = this.#refusals.get(event.aggregateId) ?? 0;
    if (refusals > 0) {
      this.#refusals.set(event.aggregateId, refusals - 1);
      throw new PublishFailed(event.id);
    }
    const delivered = { ...event };
    this.#log.push(delivered);
    for (const listener of this.#listeners) {
      listener(delivered);
    }
    if (this.#lostAcks.delete(event.aggregateId)) {
      throw new PublishFailed(event.id);
    }
  }

  /** Everything delivered so far, duplicates included, in order. */
  log(): BrokerEvent[] {
    return [...this.#log];
  }
}
