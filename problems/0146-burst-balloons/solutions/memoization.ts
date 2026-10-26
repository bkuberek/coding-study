export function maxCoins(nums: number[]): number {
  // Pad with the virtual balloons of value 1 at both ends.
  const values = [1, ...nums, 1];
  // best[left][right] caches the most coins from bursting every balloon strictly between
  // left and right, while those two are still standing; -1 is unknown.
  const best = Array.from({ length: values.length }, () => new Int32Array(values.length).fill(-1));
  const solve = (left: number, right: number): number => {
    if (right - left < 2) {
      return 0;
    }
    if (best[left][right] < 0) {
      let most = 0;
      // The balloon burst last between them has exactly left and right as neighbors.
      for (let last = left + 1; last < right; last++) {
        const coins = solve(left, last) + values[left] * values[last] * values[right] + solve(last, right);
        most = Math.max(most, coins);
      }
      best[left][right] = most;
    }
    return best[left][right];
  };
  return solve(0, values.length - 1);
}
