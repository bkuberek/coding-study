/** The balance of every open account, by account id. */
export type Balances = Map<string, number>;

export function isOpen(balances: Balances, accountId: string): boolean {
  return balances.has(accountId);
}
