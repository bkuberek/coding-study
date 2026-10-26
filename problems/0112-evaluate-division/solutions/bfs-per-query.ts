export function calcEquation(equations: string[][], values: number[], queries: string[][]): number[] {
  // graph.get(a).get(b) is the value of a / b, stored in both directions.
  const graph = new Map<string, Map<string, number>>();
  const link = (from: string, to: string, value: number): void => {
    let edges = graph.get(from);
    if (edges === undefined) {
      edges = new Map();
      graph.set(from, edges);
    }
    edges.set(to, value);
  };
  equations.forEach(([a, b], i) => {
    link(a, b, values[i]);
    link(b, a, 1 / values[i]);
  });

  const ratio = (source: string, target: string): number => {
    if (!graph.has(source) || !graph.has(target)) return -1;
    // product.get(x) is the value of source / x along the path that reached x.
    const product = new Map<string, number>([[source, 1]]);
    const queue = [source];
    for (let head = 0; head < queue.length; head++) {
      const node = queue[head];
      if (node === target) return product.get(node)!;
      for (const [neighbor, value] of graph.get(node)!) {
        if (!product.has(neighbor)) {
          product.set(neighbor, product.get(node)! * value);
          queue.push(neighbor);
        }
      }
    }
    return -1;
  };

  return queries.map(([c, d]) => ratio(c, d));
}
