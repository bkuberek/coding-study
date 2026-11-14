class Account {
  readonly id: string;
  readonly createdAt: number;
  balance = 0;
  outgoing = 0;
  closedAt: number | null = null;
  // Times and balances after each change, in time order: the account's balance history.
  private readonly times: number[] = [];
  private readonly balances: number[] = [];

  constructor(id: string, createdAt: number) {
    this.id = id;
    this.createdAt = createdAt;
    this.changeBalance(createdAt, 0);
  }

  changeBalance(timestamp: number, delta: number): number {
    this.balance += delta;
    this.times.push(timestamp);
    this.balances.push(this.balance);
    return this.balance;
  }

  balanceAt(moment: number): number {
    if (moment < this.createdAt || (this.closedAt !== null && moment >= this.closedAt)) {
      return -1;
    }
    let low = 0;
    let high = this.times.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (this.times[middle] <= moment) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return this.balances[low - 1];
  }

  canSend(target: Account, amount: number): boolean {
    return this !== target && this.balance >= amount;
  }

  send(target: Account, timestamp: number, amount: number): number {
    target.changeBalance(timestamp, amount);
    this.outgoing += amount;
    return this.changeBalance(timestamp, -amount);
  }
}

interface ScheduledTransfer {
  readonly id: string;
  readonly number: number;
  readonly sourceId: string;
  readonly targetId: string;
  readonly amount: number;
  readonly due: number;
  pending: boolean;
}

// A binary min-heap: TypeScript has no priority queue in its standard library.
class MinHeap<T> {
  private readonly items: T[] = [];
  private readonly before: (a: T, b: T) => boolean;

  constructor(before: (a: T, b: T) => boolean) {
    this.before = before;
  }

  get size(): number {
    return this.items.length;
  }

  peek(): T | undefined {
    return this.items[0];
  }

  push(item: T): void {
    this.items.push(item);
    let child = this.items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >>> 1;
      if (!this.before(this.items[child], this.items[parent])) {
        break;
      }
      this.swap(child, parent);
      child = parent;
    }
  }

  pop(): T | undefined {
    const top = this.items[0];
    const last = this.items.pop();
    if (this.items.length > 0 && last !== undefined) {
      this.items[0] = last;
      this.siftDown(0);
    }
    return top;
  }

  private siftDown(start: number): void {
    let parent = start;
    for (;;) {
      let smallest = parent;
      for (const child of [2 * parent + 1, 2 * parent + 2]) {
        if (child < this.items.length && this.before(this.items[child], this.items[smallest])) {
          smallest = child;
        }
      }
      if (smallest === parent) {
        return;
      }
      this.swap(parent, smallest);
      parent = smallest;
    }
  }

  private swap(i: number, j: number): void {
    [this.items[i], this.items[j]] = [this.items[j], this.items[i]];
  }
}

export class Bank {
  private readonly accounts = new Map<string, Account>();
  private readonly mergedInto = new Map<string, string>();
  private readonly transfers = new Map<string, ScheduledTransfer>();
  // Earliest due first, ties in scheduling order. A cancelled transfer stays in the heap and is
  // dropped when it reaches the top.
  private readonly due = new MinHeap<ScheduledTransfer>(
    (a, b) => a.due < b.due || (a.due === b.due && a.number < b.number),
  );

  // Level 1
  createAccount(timestamp: number, accountId: string): boolean {
    this.settle(timestamp);
    if (this.accounts.has(accountId)) {
      return false;
    }
    this.accounts.set(accountId, new Account(accountId, timestamp));
    return true;
  }

  deposit(timestamp: number, accountId: string, amount: number): number {
    this.settle(timestamp);
    const account = this.open(accountId);
    return account === null ? -1 : account.changeBalance(timestamp, amount);
  }

  transfer(timestamp: number, sourceId: string, targetId: string, amount: number): number {
    this.settle(timestamp);
    const source = this.open(sourceId);
    const target = this.open(targetId);
    if (source === null || target === null || !source.canSend(target, amount)) {
      return -1;
    }
    return source.send(target, timestamp, amount);
  }

  // Level 2
  topSpenders(timestamp: number, n: number): string[] {
    this.settle(timestamp);
    return [...this.accounts.values()]
      .filter((account) => account.closedAt === null)
      .sort((a, b) => b.outgoing - a.outgoing || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))
      .slice(0, n)
      .map((account) => `${account.id}(${account.outgoing})`);
  }

  // Level 3
  scheduleTransfer(
    timestamp: number,
    sourceId: string,
    targetId: string,
    amount: number,
    delay: number,
  ): string {
    this.settle(timestamp);
    const source = this.open(sourceId);
    const target = this.open(targetId);
    if (source === null || target === null || source === target) {
      return "";
    }
    const number = this.transfers.size + 1;
    const scheduled: ScheduledTransfer = {
      id: `transfer${number}`,
      number,
      sourceId,
      targetId,
      amount,
      due: timestamp + delay,
      pending: true,
    };
    this.transfers.set(scheduled.id, scheduled);
    this.due.push(scheduled);
    return scheduled.id;
  }

  cancelTransfer(timestamp: number, accountId: string, transferId: string): boolean {
    this.settle(timestamp);
    const scheduled = this.transfers.get(transferId);
    if (this.open(accountId) === null || scheduled === undefined || !scheduled.pending) {
      return false;
    }
    if (this.owner(scheduled.sourceId) !== accountId) {
      return false;
    }
    scheduled.pending = false;
    return true;
  }

  // Level 4
  mergeAccounts(timestamp: number, accountId: string, otherId: string): boolean {
    this.settle(timestamp);
    const account = this.open(accountId);
    const other = this.open(otherId);
    if (account === null || other === null || account === other) {
      return false;
    }
    account.changeBalance(timestamp, other.balance);
    account.outgoing += other.outgoing;
    other.closedAt = timestamp;
    this.mergedInto.set(otherId, accountId);
    return true;
  }

  getBalance(timestamp: number, accountId: string, timeAt: number): number {
    this.settle(timestamp);
    return this.accounts.get(accountId)?.balanceAt(timeAt) ?? -1;
  }

  private open(accountId: string): Account | null {
    const account = this.accounts.get(accountId);
    return account !== undefined && account.closedAt === null ? account : null;
  }

  // The open account that now holds `accountId`, following merges.
  private owner(accountId: string): string {
    let current = accountId;
    for (let next = this.mergedInto.get(current); next !== undefined; next = this.mergedInto.get(current)) {
      current = next;
    }
    return current;
  }

  // Run every scheduled transfer due at or before `timestamp`, each at its own due time.
  private settle(timestamp: number): void {
    for (let next = this.due.peek(); next !== undefined && next.due <= timestamp; next = this.due.peek()) {
      this.due.pop();
      if (!next.pending) {
        continue;
      }
      next.pending = false;
      const source = this.accounts.get(this.owner(next.sourceId));
      const target = this.accounts.get(this.owner(next.targetId));
      if (source !== undefined && target !== undefined && source.canSend(target, next.amount)) {
        source.send(target, next.due, next.amount);
      }
    }
  }
}
