export function networkDelayTime(times: number[][], n: number, k: number): number {
  const arrival = new Array<number>(n + 1).fill(Infinity);
  arrival[k] = 0;
  // After round i, every node whose fastest route uses at most i links has its final time;
  // a fastest route has at most n - 1 links, and a round without changes ends early.
  for (let round = 1; round < n; round++) {
    let changed = false;
    for (const [u, v, w] of times) {
      if (arrival[u] + w < arrival[v]) {
        arrival[v] = arrival[u] + w;
        changed = true;
      }
    }
    if (!changed) break;
  }
  let latest = 0;
  for (let node = 1; node <= n; node++) latest = Math.max(latest, arrival[node]);
  return latest === Infinity ? -1 : latest;
}
