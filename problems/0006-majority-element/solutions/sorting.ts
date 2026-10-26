export function majorityElement(nums: number[]): number {
  // A typed array copy sorts numerically by default and leaves `nums` untouched.
  const ordered = Int32Array.from(nums).sort();
  return ordered[Math.floor(ordered.length / 2)];
}
