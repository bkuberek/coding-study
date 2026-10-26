export function singleNumber(nums: number[]): number {
  const counts = new Map<number, number>();
  for (const value of nums) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  for (const [value, count] of counts) {
    if (count === 1) {
      return value;
    }
  }
  throw new Error("no value occurs exactly once");
}
