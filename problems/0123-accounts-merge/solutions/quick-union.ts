export function accountsMerge(accounts: string[][]): string[][] {
  const parent = accounts.map((_, x) => x); // parent[x] === x marks a root
  const find = (x: number): number => {
    while (parent[x] !== x) {
      x = parent[x];
    }
    return x;
  };
  const firstOwner = new Map<string, number>(); // address -> first account that listed it
  accounts.forEach((account, i) => {
    for (const address of account.slice(1)) {
      const owner = firstOwner.get(address);
      if (owner === undefined) {
        firstOwner.set(address, i);
        continue;
      }
      const rootOwner = find(owner);
      const rootHere = find(i);
      if (rootOwner !== rootHere) {
        parent[rootOwner] = rootHere; // no balancing: trees can grow into long chains
      }
    }
  });
  const addressesByRoot = new Map<number, Set<string>>();
  accounts.forEach((account, i) => {
    const root = find(i);
    const addresses = addressesByRoot.get(root) ?? new Set<string>();
    account.slice(1).forEach((address) => addresses.add(address));
    addressesByRoot.set(root, addresses);
  });
  // The default sort compares UTF-16 code units, which is character-code order here.
  return [...addressesByRoot].map(([root, addresses]) => [accounts[root][0], ...[...addresses].sort()]);
}
