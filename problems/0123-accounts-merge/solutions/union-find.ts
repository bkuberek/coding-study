class DisjointSets {
  private readonly parent: number[];
  private readonly size: number[]; // size[r]: number of accounts in the tree rooted at r

  constructor(count: number) {
    this.parent = Array.from({ length: count }, (_, x) => x);
    this.size = new Array<number>(count).fill(1);
  }

  find(x: number): number {
    let root = x;
    while (this.parent[root] !== root) {
      root = this.parent[root];
    }
    while (this.parent[x] !== root) {
      // Path compression: point every node on the path at the root.
      const next = this.parent[x];
      this.parent[x] = root;
      x = next;
    }
    return root;
  }

  union(a: number, b: number): void {
    let rootA = this.find(a);
    let rootB = this.find(b);
    if (rootA === rootB) {
      return;
    }
    if (this.size[rootA] < this.size[rootB]) {
      [rootA, rootB] = [rootB, rootA];
    }
    this.parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
    this.size[rootA] += this.size[rootB];
  }
}

export function accountsMerge(accounts: string[][]): string[][] {
  const sets = new DisjointSets(accounts.length);
  const firstOwner = new Map<string, number>(); // address -> first account that listed it
  accounts.forEach((account, i) => {
    for (const address of account.slice(1)) {
      const owner = firstOwner.get(address);
      if (owner === undefined) {
        firstOwner.set(address, i);
      } else {
        sets.union(owner, i);
      }
    }
  });
  const addressesByRoot = new Map<number, Set<string>>();
  accounts.forEach((account, i) => {
    const root = sets.find(i);
    const addresses = addressesByRoot.get(root) ?? new Set<string>();
    account.slice(1).forEach((address) => addresses.add(address));
    addressesByRoot.set(root, addresses);
  });
  // The default sort compares UTF-16 code units, which is character-code order here.
  return [...addressesByRoot].map(([root, addresses]) => [accounts[root][0], ...[...addresses].sort()]);
}
