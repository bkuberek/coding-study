export function checkSubarraySum(nums: number[], k: number): boolean {
  // firstIndex maps a prefix remainder to the earliest position where it appeared;
  // the empty prefix ends at position -1.
  const firstIndex = new Map<number, number>([[0, -1]]);
  let remainder = 0;
  for (let position = 0; position < nums.length; position++) {
    remainder = (remainder + nums[position]) % k;
    const earlier = firstIndex.get(remainder);
    if (earlier === undefined) {
      firstIndex.set(remainder, position);
    } else if (position - earlier >= 2) {
      return true;
    }
  }
  return false;
}
