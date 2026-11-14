export function splitArray(nums: number[], k: number): number {
  const n = nums.length;
  const prefix = [0];
  for (const value of nums) {
    prefix.push(prefix[prefix.length - 1] + value);
  }
  // best[i]: the smallest cost of cutting the first i values into the current number of pieces.
  let best = prefix.slice();
  for (let pieces = 2; pieces <= k; pieces++) {
    const next = new Array<number>(n + 1).fill(0);
    for (let end = pieces; end <= n; end++) {
      let cost = Infinity;
      for (let cut = pieces - 1; cut < end; cut++) {
        cost = Math.min(cost, Math.max(best[cut], prefix[end] - prefix[cut]));
      }
      next[end] = cost;
    }
    best = next;
  }
  return best[n];
}
