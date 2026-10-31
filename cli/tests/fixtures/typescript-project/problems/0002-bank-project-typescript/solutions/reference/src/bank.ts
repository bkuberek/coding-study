import { Ledger } from "./ledger.ts";

/** Accounts that hold a balance; the ledger keeps them. */
export class Bank {
  readonly #ledger = new Ledger();

  createAccount(timestamp: number, accountId: string): boolean {
    return this.#ledger.open(accountId);
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    return this.#ledger.add(accountId, amount);
  }

  transfer(timestamp: number, sourceId: string, targetId: string, amount: number): number {
    return this.#ledger.move(sourceId, targetId, amount);
  }
}
