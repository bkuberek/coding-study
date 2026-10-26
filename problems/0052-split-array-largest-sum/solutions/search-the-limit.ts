export function splitArray(nums: number[], k: number): number {
  // Feasibility only improves as the limit grows: find the smallest feasible limit.
  let low = 0;
  let high = 0;
  for (const value of nums) {
    low = Math.max(low, value);
    high += value;
  }
  while (low < high) {
    const limit = Math.floor((low + high) / 2);
    if (piecesNeeded(nums, limit) <= k) {
      high = limit;
    } else {
      low = limit + 1;
    }
  }
  return low;
}

// Greedy: extend the current piece while it fits under the limit.
function piecesNeeded(nums: number[], limit: number): number {
  let pieces = 1;
  let running = 0;
  for (const value of nums) {
    if (running + value > limit) {
      pieces++;
      running = value;
    } else {
      running += value;
    }
  }
  return pieces;
}
