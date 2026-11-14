// A pair is packed into one number: cost * 2^20 + i * 2^10 + j (below 2^43, so exact).
const INDEX_BITS = 1024;

export function minCostConnectPoints(points: number[][]): number {
  const n = points.length;
  const pairs = new Float64Array((n * (n - 1)) / 2);
  let next = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const cost = Math.abs(points[i][0] - points[j][0]) + Math.abs(points[i][1] - points[j][1]);
      pairs[next++] = (cost * INDEX_BITS + i) * INDEX_BITS + j;
    }
  }
  pairs.sort(); // typed arrays sort numerically

  const parent = Int32Array.from({ length: n }, (_, i) => i);
  const find = (node: number): number => {
    let root = node;
    while (parent[root] !== root) root = parent[root];
    while (parent[node] !== root) {
      const up = parent[node];
      parent[node] = root;
      node = up;
    }
    return root;
  };

  let total = 0;
  let cables = 0;
  // Take pairs from cheapest to most expensive, keeping each one that joins two groups.
  for (let index = 0; index < pairs.length && cables < n - 1; index++) {
    const packed = pairs[index];
    const j = packed % INDEX_BITS;
    const i = Math.floor(packed / INDEX_BITS) % INDEX_BITS;
    const rootI = find(i);
    const rootJ = find(j);
    if (rootI !== rootJ) {
      parent[rootI] = rootJ;
      total += Math.floor(packed / (INDEX_BITS * INDEX_BITS));
      cables++;
    }
  }
  return total;
}
