export function topKFrequent(nums: number[], k: number): number[] {
  const counts = new Map<number, number>();
  for (const value of nums) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  // buckets[c] holds the values that occur exactly c times; no count exceeds nums.length.
  const buckets: number[][] = Array.from({ length: nums.length + 1 }, () => []);
  for (const [value, count] of counts) {
    buckets[count].push(value);
  }
  const answer: number[] = [];
  for (let count = nums.length; count > 0; count--) {
    for (const value of buckets[count]) {
      answer.push(value);
      if (answer.length === k) {
        return answer;
      }
    }
  }
  return answer;
}
