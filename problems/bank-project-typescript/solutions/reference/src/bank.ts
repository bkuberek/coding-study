// The bank: the class that `cstudy submit` and the tests drive.

import { Accounts } from "./accounts.ts";
import type { Account } from "./models.ts";
import { TransferScheduler } from "./scheduler.ts";

const FAILED = -1;
const NOT_BOOKED = "";

/**
 * Bank accounts that hold whole amounts of money and send money to one another.
 *
 * Every public method first runs the scheduled transfers that fell due by its timestamp, so it
 * sees the bank as it is at that moment.
 */
export class Bank {
  readonly #accounts = new Accounts();
  readonly #scheduler = new TransferScheduler();

  createAccount(timestamp: number, accountId: string): boolean {
    this.#settle(timestamp);
    return this.#accounts.create(timestamp, accountId);
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    this.#settle(timestamp);
    return this.#accounts.findOpen(accountId)?.deposit(timestamp, amount) ?? FAILED;
  }

  transfer(timestamp: number, sourceId: string, targetId: string, amount: number): number {
    this.#settle(timestamp);
    const source = this.#accounts.findOpen(sourceId);
    const target = this.#accounts.findOpen(targetId);
    if (source === undefined || target === undefined || !source.canSend(target, amount)) {
      return FAILED;
    }
    return source.send(target, timestamp, amount);
  }

  topSpenders(timestamp: number, n: number): string[] {
    this.#settle(timestamp);
    return this.#accounts
      .open()
      .sort(bySpending)
      .slice(0, n)
      .map((account) => `${account.id}(${account.sent})`);
  }

  scheduleTransfer(
    timestamp: number,
    sourceId: string,
    targetId: string,
    amount: number,
    delay: number,
  ): string {
    this.#settle(timestamp);
    const source = this.#accounts.findOpen(sourceId);
    const target = this.#accounts.findOpen(targetId);
    if (source === undefined || target === undefined || source === target) return NOT_BOOKED;
    return this.#scheduler.book({ sourceId, targetId, amount, due: timestamp + delay });
  }

  cancelTransfer(timestamp: number, accountId: string, transferId: string): boolean {
    this.#settle(timestamp);
    const transfer = this.#scheduler.findPending(transferId);
    if (transfer === undefined) return false;
    if (this.#accounts.holderOf(transfer.sourceId)?.id !== accountId) return false;
    return this.#scheduler.cancel(transferId);
  }

  mergeAccounts(timestamp: number, accountId: string, otherId: string): boolean {
    this.#settle(timestamp);
    return this.#accounts.merge(timestamp, accountId, otherId);
  }

  getBalance(timestamp: number, accountId: string, timeAt: number): number {
    this.#settle(timestamp);
    return this.#accounts.find(accountId)?.balanceAt(timeAt) ?? FAILED;
  }

  /** Runs every scheduled transfer due by `timestamp`, each at its own due time. */
  #settle(timestamp: number): void {
    for (const { sourceId, targetId, amount, due } of this.#scheduler.takeDue(timestamp)) {
      const source = this.#accounts.holderOf(sourceId);
      const target = this.#accounts.holderOf(targetId);
      if (source !== undefined && target !== undefined && source.canSend(target, amount)) {
        source.send(target, due, amount);
      }
    }
  }
}

/** Larger totals sent first; equal totals by id, compared as strings, not by locale. */
function bySpending(a: Account, b: Account): number {
  return b.sent - a.sent || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}
