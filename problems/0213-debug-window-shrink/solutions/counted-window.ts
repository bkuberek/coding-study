export function maxDistinctWindowSum(nums: number[], k: number): number {
  const counts = new Map<number, number>();
  let windowSum = 0;
  let best = 0;
  for (let right = 0; right < nums.length; right++) {
    const value = nums[right];
    counts.set(value, (counts.get(value) ?? 0) + 1);
    windowSum += value;
    if (right >= k) {
      const outgoing = nums[right - k];
      const remaining = counts.get(outgoing)! - 1;
      if (remaining === 0) {
        counts.delete(outgoing);
      } else {
        counts.set(outgoing, remaining);
      }
      windowSum -= outgoing;
    }
    if (right >= k - 1 && counts.size === k) {
      best = Math.max(best, windowSum);
    }
  }
  return best;
}
