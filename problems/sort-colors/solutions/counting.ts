export function sortColors(nums: number[]): void {
  const counts = [0, 0, 0];
  for (const color of nums) {
    counts[color]++;
  }
  nums.fill(0, 0, counts[0]);
  nums.fill(1, counts[0], counts[0] + counts[1]);
  nums.fill(2, counts[0] + counts[1]);
}
