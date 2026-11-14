// Transfers booked to run later, handed out in the order they fall due.

import { MinHeap } from "./heap.ts";

/**
 * Money booked to move from `sourceId` to `targetId` at time `due`. The ids are those given at
 * booking time: a merge may hand them to another account, which the bank resolves when it runs.
 */
export interface ScheduledTransfer {
  readonly sourceId: string;
  readonly targetId: string;
  readonly amount: number;
  readonly due: number;
}

/** A transfer as the scheduler keeps it: its place in booking order and whether it still waits. */
interface Booking {
  readonly transfer: ScheduledTransfer;
  readonly number: number;
  pending: boolean;
}

function runOrder(a: Booking, b: Booking): number {
  return a.transfer.due - b.transfer.due || a.number - b.number;
}

/**
 * Numbers booked transfers and hands them out by due time, ties in booking order. A cancelled
 * booking stays in the heap and is dropped when it reaches the top, since a heap can only remove
 * its top cheaply.
 */
export class TransferScheduler {
  readonly #bookings = new Map<string, Booking>();
  readonly #queue = new MinHeap(runOrder);

  /** Queues `transfer` and returns its id, `transfer<k>` for the k-th booking. */
  book(transfer: ScheduledTransfer): string {
    const booking: Booking = { transfer, number: this.#bookings.size + 1, pending: true };
    const transferId = `transfer${booking.number}`;
    this.#bookings.set(transferId, booking);
    this.#queue.push(booking);
    return transferId;
  }

  /** The transfer booked as `transferId` while it still waits to run; undefined otherwise. */
  findPending(transferId: string): ScheduledTransfer | undefined {
    const booking = this.#bookings.get(transferId);
    return booking?.pending ? booking.transfer : undefined;
  }

  /** Stops a waiting transfer from running; false when it is not waiting. */
  cancel(transferId: string): boolean {
    const booking = this.#bookings.get(transferId);
    if (!booking?.pending) return false;
    booking.pending = false;
    return true;
  }

  /** Removes and returns the waiting transfers due by `timestamp`, in run order. */
  takeDue(timestamp: number): ScheduledTransfer[] {
    const due: ScheduledTransfer[] = [];
    let next = this.#queue.peek();
    while (next !== undefined && next.transfer.due <= timestamp) {
      this.#queue.pop();
      if (next.pending) {
        next.pending = false;
        due.push(next.transfer);
      }
      next = this.#queue.peek();
    }
    return due;
  }
}
