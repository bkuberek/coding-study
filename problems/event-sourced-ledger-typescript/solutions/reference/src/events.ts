// What can happen to an account, as the store keeps it, and what each event does to its balance.
// `evolve` is the one place that says so: each append, the rebuild and a balance in the past all
// fold events through it, so none of them can disagree with another.

export type EventType = "deposited" | "withdrawn" | "transferred_out" | "transferred_in";
export type LedgerEvent = { type: EventType; data: { amount: number; from?: string; to?: string } };
export type Account = { account: string; balance: number; version: number };

const DIRECTION: Record<EventType, number> = {
  deposited: 1,
  transferred_in: 1,
  withdrawn: -1,
  transferred_out: -1,
};

// An account before its first event, where every fold starts.
export function unopened(account: string): Account {
  return { account, balance: 0, version: 0 };
}

export function evolve(state: Account, event: LedgerEvent): Account {
  return {
    account: state.account,
    balance: state.balance + DIRECTION[event.type] * event.data.amount,
    version: state.version + 1,
  };
}

export function fold(account: string, events: LedgerEvent[]): Account {
  return events.reduce(evolve, unopened(account));
}
