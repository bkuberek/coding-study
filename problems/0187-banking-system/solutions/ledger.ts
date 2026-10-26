const CASHBACK_DELAY = 86_400_000;
const CASHBACK_PERCENT = 2;

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
}

interface Payment {
  readonly id: string;
  readonly accountId: string;
  readonly cashback: number;
  readonly due: number;
  received: boolean;
}

export class BankingSystem {
  private readonly accounts = new Map<string, Account>();
  private readonly mergedInto = new Map<string, string>();
  private readonly payments = new Map<string, Payment>();
  // The delay is constant and timestamps increase, so cashbacks fall due in payment order.
  private readonly pending: Payment[] = [];
  private nextPending = 0;

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
    if (source === null || target === null || source === target || source.balance < amount) {
      return -1;
    }
    target.changeBalance(timestamp, amount);
    source.outgoing += amount;
    return source.changeBalance(timestamp, -amount);
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
  pay(timestamp: number, accountId: string, amount: number): string {
    this.settle(timestamp);
    const account = this.open(accountId);
    if (account === null || account.balance < amount) {
      return "";
    }
    account.changeBalance(timestamp, -amount);
    account.outgoing += amount;
    const payment: Payment = {
      id: `payment${this.payments.size + 1}`,
      accountId,
      cashback: Math.floor((amount * CASHBACK_PERCENT) / 100),
      due: timestamp + CASHBACK_DELAY,
      received: false,
    };
    this.payments.set(payment.id, payment);
    this.pending.push(payment);
    return payment.id;
  }

  paymentStatus(timestamp: number, accountId: string, paymentId: string): string {
    this.settle(timestamp);
    const payment = this.payments.get(paymentId);
    if (this.open(accountId) === null || payment === undefined) {
      return "";
    }
    if (this.owner(payment.accountId) !== accountId) {
      return "";
    }
    return payment.received ? "CASHBACK_RECEIVED" : "IN_PROGRESS";
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

  // Credit every cashback due at or before `timestamp`, at its own due time.
  private settle(timestamp: number): void {
    while (this.nextPending < this.pending.length && this.pending[this.nextPending].due <= timestamp) {
      const payment = this.pending[this.nextPending++];
      this.accounts.get(this.owner(payment.accountId))?.changeBalance(payment.due, payment.cashback);
      payment.received = true;
    }
  }
}
