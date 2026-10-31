export class Ledger {
  readonly #balances = new Map<string, number>();

  open(id: string): boolean {
    if (this.#balances.has(id)) {
      return false;
    }
    this.#balances.set(id, 0);
    return true;
  }

  has(id: string): boolean {
    return this.#balances.has(id);
  }

  balance(id: string): number {
    return this.#balances.get(id) ?? 0;
  }

  add(id: string, amount: number): number {
    const balance = this.balance(id) + amount;
    this.#balances.set(id, balance);
    return balance;
  }

  close(id: string): void {
    this.#balances.delete(id);
  }

  ids(): string[] {
    return [...this.#balances.keys()];
  }
}
