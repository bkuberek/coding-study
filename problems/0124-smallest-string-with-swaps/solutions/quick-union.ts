export function smallestStringWithSwaps(s: string, pairs: number[][]): string {
  const parent = Array.from({ length: s.length }, (_, x) => x); // parent[x] === x marks a root
  const find = (x: number): number => {
    while (parent[x] !== x) {
      x = parent[x];
    }
    return x;
  };
  for (const [a, b] of pairs) {
    const rootA = find(a);
    const rootB = find(b);
    if (rootA !== rootB) {
      parent[rootA] = rootB; // no balancing: trees can grow into long chains
    }
  }
  // Positions are added in increasing order, so each group's list is sorted.
  const groups = new Map<number, number[]>();
  for (let position = 0; position < s.length; position++) {
    const root = find(position);
    const group = groups.get(root);
    if (group === undefined) {
      groups.set(root, [position]);
    } else {
      group.push(position);
    }
  }
  const letters = [...s];
  for (const positions of groups.values()) {
    const sorted = positions.map((position) => s[position]).sort();
    positions.forEach((position, k) => {
      letters[position] = sorted[k];
    });
  }
  return letters.join("");
}
