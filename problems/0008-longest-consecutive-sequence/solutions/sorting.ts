export function longestConsecutive(nums: number[]): number {
  if (nums.length === 0) {
    return 0;
  }
  const ordered = Int32Array.from(nums).sort();
  let longest = 1;
  let current = 1;
  for (let i = 1; i < ordered.length; i++) {
    if (ordered[i] === ordered[i - 1]) {
      continue;
    }
    current = ordered[i] === ordered[i - 1] + 1 ? current + 1 : 1;
    longest = Math.max(longest, current);
  }
  return longest;
}
