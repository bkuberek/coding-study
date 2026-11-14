export function networkDelayTime(times: number[][], n: number, k: number): number {
  const graph: [number, number][][] = Array.from({ length: n + 1 }, () => []);
  for (const [u, v, w] of times) graph[u].push([v, w]);
  const arrival = new Array<number>(n + 1).fill(Infinity);
  arrival[k] = 0;
  const settled = new Uint8Array(n + 1);
  let latest = 0;
  for (let round = 0; round < n; round++) {
    // Scan for the unsettled node with the earliest arrival: O(n) per round, no heap.
    let node = -1;
    for (let v = 1; v <= n; v++) {
      if (settled[v] === 0 && (node === -1 || arrival[v] < arrival[node])) node = v;
    }
    if (arrival[node] === Infinity) return -1;
    settled[node] = 1;
    latest = arrival[node];
    for (const [neighbor, w] of graph[node]) {
      arrival[neighbor] = Math.min(arrival[neighbor], arrival[node] + w);
    }
  }
  return latest;
}
