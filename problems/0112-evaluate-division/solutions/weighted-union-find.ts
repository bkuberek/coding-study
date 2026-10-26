export function calcEquation(equations: string[][], values: number[], queries: string[][]): number[] {
  // parent.get(x) is x's parent; weight.get(x) is the value of x / parent(x).
  const parent = new Map<string, string>();
  const weight = new Map<string, number>();

  // Returns [root, name / root] and compresses the path on the way.
  const find = (name: string): [string, number] => {
    const path: string[] = [];
    let node = name;
    while (parent.get(node) !== node) {
      path.push(node);
      node = parent.get(node)!;
    }
    const root = node;
    for (let i = path.length - 1; i >= 0; i--) {
      const current = path[i];
      const up = parent.get(current)!;
      if (up !== root) {
        weight.set(current, weight.get(current)! * weight.get(up)!);
        parent.set(current, root);
      }
    }
    return [root, path.length > 0 ? weight.get(name)! : 1];
  };

  equations.forEach(([a, b], i) => {
    for (const name of [a, b]) {
      if (!parent.has(name)) {
        parent.set(name, name);
        weight.set(name, 1);
      }
    }
    const [rootA, aOverRootA] = find(a);
    const [rootB, bOverRootB] = find(b);
    if (rootA !== rootB) {
      // Hang rootA under rootB: rootA / rootB = (a / b) * (b / rootB) / (a / rootA).
      parent.set(rootA, rootB);
      weight.set(rootA, (values[i] * bOverRootB) / aOverRootA);
    }
  });

  return queries.map(([c, d]) => {
    if (!parent.has(c) || !parent.has(d)) return -1;
    const [rootC, cOverRoot] = find(c);
    const [rootD, dOverRoot] = find(d);
    return rootC === rootD ? cOverRoot / dOverRoot : -1;
  });
}
