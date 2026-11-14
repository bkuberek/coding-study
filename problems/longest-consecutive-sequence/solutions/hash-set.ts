export function longestConsecutive(nums: number[]): number {
  const present = new Set(nums);
  let longest = 0;
  for (const value of present) {
    if (present.has(value - 1)) {
      continue;
    }
    let end = value + 1;
    while (present.has(end)) {
      end++;
    }
    longest = Math.max(longest, end - value);
  }
  return longest;
}
