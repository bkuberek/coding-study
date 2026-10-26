export function majorityElement(nums: number[]): number {
  const half = Math.floor(nums.length / 2);
  for (const candidate of nums) {
    let count = 0;
    for (const value of nums) {
      if (value === candidate) {
        count++;
      }
    }
    if (count > half) {
      return candidate;
    }
  }
  throw new Error("no majority element");
}
