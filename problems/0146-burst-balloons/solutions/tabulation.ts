export function maxCoins(nums: number[]): number {
  const values = [1, ...nums, 1];
  const size = values.length;
  // best[left][right]: most coins from bursting everything strictly between left and right.
  const best = Array.from({ length: size }, () => new Int32Array(size));
  // An interval only depends on shorter ones, so fill by increasing gap right - left.
  for (let gap = 2; gap < size; gap++) {
    for (let left = 0; left + gap < size; left++) {
      const right = left + gap;
      const outer = values[left] * values[right];
      let most = 0;
      for (let last = left + 1; last < right; last++) {
        most = Math.max(most, best[left][last] + outer * values[last] + best[last][right]);
      }
      best[left][right] = most;
    }
  }
  return best[0][size - 1];
}
