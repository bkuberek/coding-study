import { Ledger } from "./ledger.ts";

export class Bank {
  readonly #ledger = new Ledger();

  createAccount(timestamp: number, accountId: string): boolean {
    return this.#ledger.open(accountId);
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    if (!this.#ledger.has(accountId)) {
      return -1;
    }
    return this.#ledger.add(accountId, amount);
  }

  transfer(
    timestamp: number,
    sourceId: string,
    targetId: string,
    amount: number,
  ): number {
    const ledger = this.#ledger;
    const known = ledger.has(sourceId) && ledger.has(targetId);
    if (!known || sourceId === targetId || ledger.balance(sourceId) < amount) {
      return -1;
    }
    ledger.add(targetId, amount);
    return ledger.add(sourceId, -amount);
  }

  closeAccount(timestamp: number, accountId: string): void {
    this.#ledger.close(accountId);
  }

  accounts(): string[] {
    return this.#ledger.ids();
  }

  balances(): number[] {
    return this.#ledger
      .ids()
      .sort()
      .map((id) => this.#ledger.balance(id));
  }

  averageBalance(): number {
    const ids = this.#ledger.ids();
    if (ids.length === 0) {
      return 0;
    }
    const total = ids.reduce((sum, id) => sum + this.#ledger.balance(id), 0);
    return total / ids.length;
  }
}
