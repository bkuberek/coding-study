export function longestConsecutive(nums: number[]): number {
  let longest = 0;
  for (let i = 0; i < nums.length; i++) {
    const value = nums[i];
    // includes() and indexOf() are linear scans: O(n) per check.
    if (nums.includes(value - 1)) {
      continue;
    }
    if (nums.indexOf(value) < i) {
      continue; // an earlier copy of this start already counted its run
    }
    let length = 1;
    while (nums.includes(value + length)) {
      length++;
    }
    longest = Math.max(longest, length);
  }
  return longest;
}
