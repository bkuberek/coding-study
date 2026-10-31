// The bank's model types: an account and the history of its balance.

/** One change of a balance: the balance from moment `at` on. */
interface BalanceChange {
  readonly at: number;
  readonly balance: number;
}

/** An account's balance after each change, in time order. */
export class BalanceHistory {
  readonly #changes: BalanceChange[] = [];

  record(at: number, balance: number): void {
    this.#changes.push({ at, balance });
  }

  /** The balance after the last change at or before `moment`; undefined before the first. */
  balanceAt(moment: number): number | undefined {
    const count = this.#countUpTo(moment);
    return count === 0 ? undefined : this.#changes[count - 1].balance;
  }

  /** How many changes happened at or before `moment`: a binary search, as times only grow. */
  #countUpTo(moment: number): number {
    let low = 0;
    let high = this.#changes.length;
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      if (this.#changes[middle].at <= moment) low = middle + 1;
      else high = middle;
    }
    return low;
  }
}

/** When a merge folded an account into another, and which one. */
interface Merge {
  readonly into: Account;
  readonly at: number;
}

/** An account: its balance, the money it sent, its lifetime and its history. */
export class Account {
  readonly id: string;
  readonly createdAt: number;
  readonly history = new BalanceHistory();
  #balance = 0;
  #sent = 0;
  #merge: Merge | undefined;

  constructor(id: string, createdAt: number) {
    this.id = id;
    this.createdAt = createdAt;
    this.history.record(createdAt, 0);
  }

  get balance(): number {
    return this.#balance;
  }

  /** The money that left this account in transfers: what ranks the top spenders. */
  get sent(): number {
    return this.#sent;
  }

  get isOpen(): boolean {
    return this.#merge === undefined;
  }

  /** The open account that holds this account's money now: itself, or the end of its merges. */
  get holder(): Account {
    return this.#merge?.into.holder ?? this;
  }

  deposit(timestamp: number, amount: number): number {
    return this.#changeBalance(timestamp, amount);
  }

  canSend(target: Account, amount: number): boolean {
    return target !== this && this.#balance >= amount;
  }

  /** Moves `amount` to `target` and returns this account's new balance. */
  send(target: Account, timestamp: number, amount: number): number {
    target.deposit(timestamp, amount);
    this.#sent += amount;
    return this.#changeBalance(timestamp, -amount);
  }

  /** Adds `other`'s balance and money sent to this account, and closes `other` into it. */
  absorb(other: Account, timestamp: number): void {
    this.#changeBalance(timestamp, other.#balance);
    this.#sent += other.#sent;
    other.#merge = { into: this, at: timestamp };
  }

  /** The balance at `moment`; undefined when the account did not exist then. */
  balanceAt(moment: number): number | undefined {
    return this.#existedAt(moment) ? this.history.balanceAt(moment) : undefined;
  }

  #existedAt(moment: number): boolean {
    const mergedAway = this.#merge !== undefined && moment >= this.#merge.at;
    return moment >= this.createdAt && !mergedAway;
  }

  #changeBalance(timestamp: number, delta: number): number {
    this.#balance += delta;
    this.history.record(timestamp, this.#balance);
    return this.#balance;
  }
}
