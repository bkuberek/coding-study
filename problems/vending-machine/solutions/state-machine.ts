type State = "MAINTENANCE" | "IDLE" | "HAS_CREDIT";

// The coins inside the machine, by denomination; pays out exact change with the fewest coins.
class CoinBox {
  private readonly counts = new Map<number, number>(); // largest denomination first

  constructor(denominations: readonly number[]) {
    for (const coin of [...denominations].sort((a, b) => b - a)) {
      this.counts.set(coin, 0);
    }
  }

  accepts(coin: number): boolean {
    return this.counts.has(coin);
  }

  add(coin: number, count = 1): void {
    this.counts.set(coin, (this.counts.get(coin) ?? 0) + count);
  }

  // Remove and return coins worth `amount`, or null (changing nothing) when impossible.
  payOut(amount: number): number[] | null {
    const coins = this.plan(amount);
    for (const coin of coins ?? []) {
      this.add(coin, -1);
    }
    return coins;
  }

  // Fewest coins; among those, as many of the largest coin as possible, then the next.
  private plan(amount: number): number[] | null {
    const stock = [...this.counts.entries()];
    // fewest[i][a]: fewest coins making `a` from denominations i and smaller.
    const fewest = Array.from({ length: stock.length + 1 }, () => new Array<number>(amount + 1).fill(Infinity));
    fewest[stock.length][0] = 0;
    for (let i = stock.length - 1; i >= 0; i--) {
      const [coin, available] = stock[i];
      for (let a = 0; a <= amount; a++) {
        for (let k = 0; k <= Math.min(available, Math.floor(a / coin)); k++) {
          fewest[i][a] = Math.min(fewest[i][a], k + fewest[i + 1][a - k * coin]);
        }
      }
    }
    if (fewest[0][amount] === Infinity) {
      return null;
    }
    const coins: number[] = [];
    let remaining = amount;
    stock.forEach(([coin, available], i) => {
      for (let k = Math.min(available, Math.floor(remaining / coin)); k >= 0; k--) {
        if (k + fewest[i + 1][remaining - k * coin] === fewest[i][remaining]) {
          coins.push(...new Array<number>(k).fill(coin));
          remaining -= k * coin;
          return;
        }
      }
    });
    return coins;
  }
}

interface Slot {
  price: number;
  count: number;
}

export class VendingMachine {
  private currentState: State = "MAINTENANCE";
  private readonly coins: CoinBox;
  private readonly slots = new Map<string, Slot>();
  private credit = 0;
  private tray: number[] = [];

  constructor(denominations: number[]) {
    this.coins = new CoinBox(denominations);
  }

  service(enabled: boolean): boolean {
    if (enabled && this.currentState === "IDLE") {
      this.currentState = "MAINTENANCE";
      return true;
    }
    if (!enabled && this.currentState === "MAINTENANCE") {
      this.currentState = "IDLE";
      return true;
    }
    return false;
  }

  stock(slot: string, price: number, count: number): boolean {
    if (this.currentState !== "MAINTENANCE") {
      return false;
    }
    const item = this.slots.get(slot);
    this.slots.set(slot, { price, count: (item?.count ?? 0) + count });
    return true;
  }

  loadCoins(coin: number, count: number): boolean {
    if (this.currentState !== "MAINTENANCE" || !this.coins.accepts(coin)) {
      return false;
    }
    this.coins.add(coin, count);
    return true;
  }

  insert(coin: number): number {
    if (this.currentState === "MAINTENANCE" || !this.coins.accepts(coin)) {
      this.tray.push(coin);
      return -1;
    }
    this.coins.add(coin);
    this.credit += coin;
    this.currentState = "HAS_CREDIT";
    return this.credit;
  }

  select(slot: string): string {
    if (this.currentState === "MAINTENANCE") {
      return "OUT_OF_SERVICE";
    }
    const item = this.slots.get(slot);
    if (item === undefined) {
      return "UNKNOWN_SLOT";
    }
    if (item.count === 0) {
      return "SOLD_OUT";
    }
    if (this.credit < item.price) {
      return "INSUFFICIENT_CREDIT";
    }
    const change = this.coins.payOut(this.credit - item.price);
    if (change === null) {
      return "NO_CHANGE";
    }
    item.count--;
    this.finish(change);
    return "DISPENSED";
  }

  refund(): number {
    if (this.currentState !== "HAS_CREDIT") {
      return 0;
    }
    const amount = this.credit;
    this.finish(this.coins.payOut(amount) ?? []);
    return amount;
  }

  collect(): number[] {
    const coins = this.tray.sort((a, b) => b - a);
    this.tray = [];
    return coins;
  }

  state(): string {
    return this.currentState;
  }

  stockOf(slot: string): number {
    return this.slots.get(slot)?.count ?? -1;
  }

  // Return change to the tray and end the transaction.
  private finish(change: readonly number[]): void {
    this.tray.push(...change);
    this.credit = 0;
    this.currentState = "IDLE";
  }
}
