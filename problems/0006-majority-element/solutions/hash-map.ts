export function majorityElement(nums: number[]): number {
  const half = Math.floor(nums.length / 2);
  const counts = new Map<number, number>();
  for (const value of nums) {
    const count = (counts.get(value) ?? 0) + 1;
    if (count > half) {
      return value;
    }
    counts.set(value, count);
  }
  throw new Error("no majority element");
}
